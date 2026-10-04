"""Concurrent cutover lock measurements for the frozen Gate738H candidate.

Run only on a loopback-only disposable PostgreSQL 16/pgvector cluster with
GATE738H_DISPOSABLE=1 and GATE738H_ADMIN_DSN pointing at its postgres DB.
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DSN = os.environ["GATE738H_ADMIN_DSN"]
assert os.environ.get("GATE738H_DISPOSABLE") == "1"
parsed = urlparse(ADMIN_DSN)
assert parsed.scheme in {"postgres", "postgresql"}
assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
assert parsed.path.lstrip("/") == "postgres"


def dsn(database: str, *, sqlalchemy: bool = False) -> str:
    value = urlunparse(parsed._replace(path=f"/{database}"))
    return value.replace("postgresql://", "postgresql+asyncpg://", 1) if sqlalchemy else value


def command(args: list[str], database: str, timeout: int = 240) -> tuple[float, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
    env["GATE738E_DISPOSABLE"] = "1"
    started = time.perf_counter()
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True,
                            timeout=timeout, check=False)
    elapsed = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(f"{args[-1]} failed: {result.stderr[-2500:]}")
    return elapsed, result.stdout + result.stderr


def alembic(database: str, revision: str) -> float:
    elapsed, _ = command([sys.executable, "-B", "-m", "alembic", "upgrade", revision], database)
    return elapsed


async def prepare(database: str, count: int) -> None:
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
    finally:
        await admin.close()
    alembic(database, "20260921_0022")
    connection = await asyncpg.connect(dsn(database))
    try:
        teacher = await connection.fetchval("INSERT INTO users(role) VALUES('TEACHER') RETURNING id")
        profile = await connection.fetchval(
            "INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES($1,'gate738h-lock') RETURNING id",
            teacher,
        )
        classroom = await connection.fetchval(
            "INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id) "
            "VALUES('gate738h-lock','gate738h-lock',$1) RETURNING id", profile,
        )
        assignment = await connection.fetchval(
            "INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) "
            "VALUES($1,$2,'gate738h-lock','synthetic','PUBLISHED') RETURNING id", teacher, classroom,
        )
        user_start = await connection.fetchval("SELECT coalesce(max(id),0)+1 FROM users")
        await connection.execute(
            "INSERT INTO users(id,role) SELECT $1+g,'STUDENT' FROM generate_series(0,$2-1) g",
            user_start, count,
        )
        await connection.execute(
            "SELECT setval('users_id_seq',GREATEST((SELECT max(id) FROM users),1))"
        )
        await connection.execute(
            "INSERT INTO student_profiles(student_id) SELECT $1+g FROM generate_series(0,$2-1) g",
            user_start, count,
        )
        profile_start = await connection.fetchval(
            "SELECT min(id) FROM student_profiles WHERE student_id >= $1", user_start,
        )
        await connection.execute("""
            INSERT INTO student_submissions
                (assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
            SELECT $1,$2+g,'gate738h-lock','SUBMITTED',1,'{"synthetic":true}',now()
              FROM generate_series(0,$3-1) g
        """, assignment, profile_start, count)
        reviews = max(1, count // 20)
        await connection.execute("""
            INSERT INTO submission_reviews(submission_id,tenant_id,review_status,score,teacher_feedback,reviewed_by)
            SELECT id,'gate738h-lock','REVIEWED',8,'synthetic',$1
              FROM student_submissions ORDER BY id LIMIT $2
        """, teacher, reviews)
    finally:
        await connection.close()
    for revision in ("20261003_0027", "20261003_0028", "20261003_0029"):
        alembic(database, revision)
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
    env["GATE738E_DISPOSABLE"] = "1"
    _, _ = command([sys.executable, "-B", "scripts/backfill_submission_revisions.py",
                    "--batch-size", "1000", "--idle-timeout-seconds", "3"], database)


async def measure(label: str, count: int) -> dict:
    database = "gate738e_gate738h_lock_" + uuid4().hex
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await prepare(database, count)
        connection = await asyncpg.connect(dsn(database))
        before = await connection.fetchrow("""
            SELECT pg_total_relation_size('student_submissions') AS parents,
                   pg_total_relation_size('submission_reviews') AS reviews,
                   pg_total_relation_size('submission_revisions') AS revisions
        """)
        stop = asyncio.Event()
        read_latencies: list[float] = []
        write_latencies: list[float] = []
        read_errors: list[str] = []
        write_errors: list[str] = []
        lock_wait_started: float | None = None
        lock_acquired_at: float | None = None
        lock_released_at: float | None = None
        wait_events: list[dict[str, str]] = []

        async def read_worker() -> None:
            reader = await asyncpg.connect(dsn(database))
            try:
                while not stop.is_set():
                    start = time.perf_counter()
                    try:
                        await reader.fetchval("SELECT count(*) FROM student_submissions")
                        read_latencies.append((time.perf_counter() - start) * 1000)
                    except asyncpg.PostgresError as error:
                        read_errors.append(error.sqlstate or type(error).__name__)
                    await asyncio.sleep(.003)
            finally:
                await reader.close()

        async def write_worker() -> None:
            writer = await asyncpg.connect(dsn(database))
            try:
                await writer.execute("SET lock_timeout='1s'")
                while not stop.is_set():
                    start = time.perf_counter()
                    try:
                        await writer.execute(
                            "UPDATE student_submissions SET updated_at=now() WHERE id=1"
                        )
                        write_latencies.append((time.perf_counter() - start) * 1000)
                    except asyncpg.PostgresError as error:
                        write_errors.append(error.sqlstate or type(error).__name__)
                    await asyncio.sleep(.003)
            finally:
                await writer.close()

        readers = [asyncio.create_task(read_worker()) for _ in range(4)]
        writers = [asyncio.create_task(write_worker()) for _ in range(2)]
        await asyncio.sleep(.1)

        async def observe_locks() -> None:
            nonlocal lock_wait_started, lock_acquired_at, lock_released_at
            while not stop.is_set():
                rows = await connection.fetch("""
                    SELECT l.mode,l.granted,c.relname,a.wait_event_type,a.wait_event
                      FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
                      JOIN pg_stat_activity a ON a.pid=l.pid
                     WHERE l.pid<>pg_backend_pid() AND c.relname='submission_reviews'
                       AND l.mode='AccessExclusiveLock'
                """)
                for row in rows:
                    now = time.perf_counter()
                    if row["granted"] and lock_acquired_at is None:
                        lock_acquired_at = now
                    elif not row["granted"] and lock_wait_started is None:
                        lock_wait_started = now
                        wait_events.append({"type": row["wait_event_type"] or "",
                                            "event": row["wait_event"] or ""})
                if lock_acquired_at is not None and not rows and lock_released_at is None:
                    lock_released_at = time.perf_counter()
                await asyncio.sleep(.002)

        observer = asyncio.create_task(observe_locks())
        migration_started = time.perf_counter()
        migration_error = None
        try:
            await asyncio.to_thread(alembic, database, "20261003_0030")
        except RuntimeError as error:  # captured as qualification evidence
            migration_error = str(error)
        migration_elapsed_ms = (time.perf_counter() - migration_started) * 1000
        await asyncio.sleep(.1)
        stop.set()
        await asyncio.gather(*readers, *writers)
        await observer
        after = await connection.fetchrow("""
            SELECT pg_total_relation_size('student_submissions') AS parents,
                   pg_total_relation_size('submission_reviews') AS reviews,
                   pg_total_relation_size('submission_revisions') AS revisions
        """)
        head = await connection.fetchval("SELECT version_num FROM alembic_version")
        await connection.close()
        if migration_error is None:
            alembic(database, "20261003_0031")
        result = {
            "tier": label, "submissions": count, "reviews": max(1, count // 20),
            "migration_head": head, "migration_error": migration_error,
            "0030_elapsed_ms": round(migration_elapsed_ms, 2),
            "access_exclusive_wait_ms": round((lock_acquired_at-lock_wait_started)*1000, 2)
                if lock_wait_started is not None and lock_acquired_at is not None else 0,
            "access_exclusive_hold_ms": round((lock_released_at-lock_acquired_at)*1000, 2)
                if lock_released_at is not None and lock_acquired_at is not None else None,
            "lock_wait_events": wait_events,
            "read_samples": len(read_latencies),
            "reader_latency_max_ms": round(max(read_latencies), 2) if read_latencies else None,
            "reader_failures": len(read_errors), "reader_failure_codes": read_errors[:10],
            "write_samples": len(write_latencies),
            "writer_latency_max_ms": round(max(write_latencies), 2) if write_latencies else None,
            "writer_latency_median_ms": round(statistics.median(write_latencies), 2)
                if write_latencies else None,
            "writer_failures": len(write_errors), "writer_failure_codes": write_errors[:10],
            "sizes_before": dict(before), "sizes_after": dict(after),
        }
        print(json.dumps(result, default=str))
        return result
    finally:
        await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        await admin.close()


async def main() -> None:
    results = [await measure("SMALL", 100), await measure("MEDIUM", 1000),
               await measure("STRESS", 5000)]
    print(json.dumps({"lock_matrix": results, "all_migrations_succeeded": all(
        row["migration_error"] is None and row["migration_head"] == "20261003_0030"
        for row in results)}, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")
