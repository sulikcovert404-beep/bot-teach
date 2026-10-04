"""Disposable-only scale/resume qualification for Gate738F.

Run only against the dedicated loopback PostgreSQL created for Gate738F:
GATE738E_LOCAL_PG_PORT=<mapped-port> python tests/gate738f_qualification.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from statistics import median
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")

PORT = int(os.environ["GATE738E_LOCAL_PG_PORT"])
assert 1 <= PORT <= 65535
assert os.environ.get("GATE738F_DISPOSABLE") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def connect(db: str) -> asyncpg.Connection:
    return await asyncpg.connect(host="127.0.0.1", port=PORT, user="gate738e", database=db)


def alembic(db: str, revision: str) -> tuple[float, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}"
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", revision],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=180, check=False)
    elapsed = time.perf_counter() - started
    if proc.returncode:
        raise RuntimeError(f"alembic {revision} failed: {proc.stderr[-3000:]}")
    return elapsed, proc.stdout + proc.stderr


def backfill(db: str, limit: int | None = 1, batch: int = 500) -> tuple[float, str, int]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}"
    env["GATE738E_DISPOSABLE"] = "1"
    args = [sys.executable, "-B", "scripts/backfill_submission_revisions.py",
            "--batch-size", str(batch), "--idle-timeout-seconds", "2"]
    if limit is not None:
        args += ["--max-batches", str(limit)]
    started = time.perf_counter()
    proc = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180, check=False)
    elapsed = time.perf_counter() - started
    if limit is None and proc.returncode:
        raise RuntimeError(f"backfill failed: {proc.stderr[-3000:]}")
    return elapsed, proc.stdout + proc.stderr, proc.returncode


async def prepare(db: str, n: int, reviews: int) -> None:
    admin = await connect("gate738e_test")
    try:
        await admin.execute(f'CREATE DATABASE "{db}"')
    finally:
        await admin.close()
    alembic(db, "20260921_0022")
    c = await connect(db)
    try:
        teacher = await c.fetchval("INSERT INTO users(role) VALUES('TEACHER') RETURNING id")
        tp = await c.fetchval("INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES($1,'gate738f') RETURNING id", teacher)
        classroom = await c.fetchval("INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id) VALUES('gate738f','gate738f',$1) RETURNING id", tp)
        assignment = await c.fetchval("INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) VALUES($1,$2,'gate738f','synthetic','PUBLISHED') RETURNING id", teacher, classroom)
        lo = await c.fetchval("SELECT coalesce(max(id),0)+1 FROM users")
        await c.execute("INSERT INTO users(id,role) SELECT $1+g,'STUDENT' FROM generate_series(0,$2-1) g", lo, n)
        await c.execute("SELECT setval('users_id_seq', GREATEST((SELECT max(id) FROM users),1))")
        await c.execute("INSERT INTO student_profiles(student_id) SELECT $1+g FROM generate_series(0,$2-1) g", lo, n)
        profile_lo = await c.fetchval("SELECT min(id) FROM student_profiles WHERE student_id >= $1", lo)
        await c.execute("""
            INSERT INTO student_submissions(assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
            SELECT $1,$2+g,'gate738f','SUBMITTED',1,'{\"synthetic\":true}',now()
              FROM generate_series(0,$3-1) g
        """, assignment, profile_lo, n)
        if reviews:
            await c.execute("""
                INSERT INTO submission_reviews(submission_id,tenant_id,review_status,score,teacher_feedback,reviewed_by)
                SELECT s.id,'gate738f','REVIEWED',8,'synthetic',$1
                  FROM student_submissions s ORDER BY s.id LIMIT $2
            """, teacher, reviews)
    finally:
        await c.close()


async def measure_tier(label: str, n: int) -> dict:
    db = "gate738e_" + uuid4().hex
    reviews = max(1, n // 20)
    await prepare(db, n, reviews)
    out: dict = {"tier": label, "submissions": n, "reviews": reviews}
    timings = {}
    for rev in ("20261003_0027", "20261003_0028", "20261003_0029"):
        timings[rev], _ = alembic(db, rev)
    c = await connect(db)
    try:
        before = await c.fetchrow("""
            SELECT pg_total_relation_size('student_submissions') AS submissions,
                   pg_total_relation_size('submission_reviews') AS reviews
        """)
    finally:
        await c.close()
    batches: list[float] = []
    done = False
    while not done:
        elapsed, output, code = backfill(db, limit=1, batch=500)
        batches.append(elapsed)
        done = code == 0
        if code and "BACKFILL_PAUSED" not in output:
            raise RuntimeError(f"unexpected pause/failure in {label}: {output[-2000:]}")
    c = await connect(db)
    try:
        state = await c.fetchrow("SELECT status,processed_submissions,processed_reviews FROM submission_revision_backfill_state")
        after = await c.fetchrow("""
            SELECT pg_total_relation_size('student_submissions') AS submissions,
                   pg_total_relation_size('submission_reviews') AS reviews,
                   pg_total_relation_size('submission_revisions') AS revisions,
                   count(*) FILTER (WHERE current_revision_id IS NULL) AS missing_pointers
              FROM student_submissions
        """)
        rev_count = await c.fetchval("SELECT count(*) FROM submission_revisions")
        missing_reviews = await c.fetchval("SELECT count(*) FROM submission_reviews WHERE submission_revision_id IS NULL")
    finally:
        await c.close()
    timings["backfill_total"] = sum(batches)
    timings["backfill_batches"] = len(batches)
    timings["batch_median_seconds"] = median(batches)
    timings["batch_max_seconds"] = max(batches)
    timings["contract_0030"], _ = alembic(db, "20261003_0030")
    timings["cleanup_0031"], _ = alembic(db, "20261003_0031")
    out.update({"timings": timings, "table_sizes_before_bytes": dict(before),
                "table_sizes_after_bytes": {k: after[k] for k in ("submissions", "reviews", "revisions")},
                "backfill_state": dict(state), "revision_rows": rev_count,
                "missing_pointer_count": after["missing_pointers"], "unlinked_review_count": missing_reviews})
    assert state["status"] == "VALIDATED" and state["processed_submissions"] == n
    assert rev_count == n and after["missing_pointers"] == 0 and missing_reviews == 0
    return out


async def main() -> None:
    results = [await measure_tier("SMALL", 100),
               await measure_tier("MEDIUM", 1000),
               await measure_tier("STRESS", 5000)]
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")
