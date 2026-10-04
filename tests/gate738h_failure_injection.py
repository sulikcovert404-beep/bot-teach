"""Failure-boundary probes for the frozen Gate738H candidate.

Only uniquely named databases on a loopback Gate-owned disposable PostgreSQL
cluster are created or dropped. Migration and application files are read-only.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
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


def alembic(database: str, revision: str, *, expect_failure: bool = False) -> str:
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "alembic", "upgrade", revision],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=240, check=False,
    )
    if expect_failure and result.returncode == 0:
        raise AssertionError(f"alembic {revision} unexpectedly succeeded")
    if not expect_failure and result.returncode:
        raise RuntimeError(f"alembic {revision}: {result.stderr[-2500:]}")
    return result.stderr[-1200:]


async def seed(connection: asyncpg.Connection) -> tuple[int, int]:
    teacher = await connection.fetchval("INSERT INTO users(role) VALUES('TEACHER') RETURNING id")
    teacher_profile = await connection.fetchval(
        "INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES($1,'gate738h-failure') RETURNING id",
        teacher,
    )
    classroom = await connection.fetchval(
        "INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id) "
        "VALUES('gate738h-failure','gate738h-failure',$1) RETURNING id", teacher_profile,
    )
    assignment = await connection.fetchval(
        "INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) "
        "VALUES($1,$2,'gate738h-failure','synthetic','PUBLISHED') RETURNING id",
        teacher, classroom,
    )
    student = await connection.fetchval("INSERT INTO users(role) VALUES('STUDENT') RETURNING id")
    profile = await connection.fetchval(
        "INSERT INTO student_profiles(student_id) VALUES($1) RETURNING id", student,
    )
    submission = await connection.fetchval("""
        INSERT INTO student_submissions
            (assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
        VALUES($1,$2,'gate738h-failure','SUBMITTED',1,'before',now()) RETURNING id
    """, assignment, profile)
    return int(teacher), int(submission)


async def parent_snapshot(connection: asyncpg.Connection, submission_id: int) -> dict:
    row = await connection.fetchrow("""
        SELECT s.status,s.revision,s.content_json,s.current_revision_id,
               (SELECT count(*) FROM submission_revisions r WHERE r.submission_id=s.id) AS revisions
          FROM student_submissions s WHERE s.id=$1
    """, submission_id)
    return dict(row)


async def install_raise_trigger(
    connection: asyncpg.Connection, *, table: str, timing: str, event: str, name: str,
    condition: str = "",
) -> None:
    allowed = {"submission_revisions", "student_submissions", "submission_reviews"}
    assert table in allowed and timing in {"BEFORE", "AFTER"} and event in {"INSERT", "UPDATE"}
    assert name.isidentifier() and (not condition or condition in {"current_revision_id"})
    function = f"{name}_fn"
    predicate = (
        " IF NEW.current_revision_id IS NOT DISTINCT FROM OLD.current_revision_id THEN "
        "RETURN NEW; END IF;" if condition == "current_revision_id" else ""
    )
    await connection.execute(f"""
        CREATE FUNCTION public.{function}() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN {predicate} RAISE EXCEPTION 'injected disposable failure' USING ERRCODE='P0001';
        END $$
    """)
    await connection.execute(
        f"CREATE TRIGGER {name} {timing} {event} ON public.{table} "
        f"FOR EACH ROW EXECUTE FUNCTION public.{function}()"
    )


async def remove_raise_trigger(connection: asyncpg.Connection, *, table: str, name: str) -> None:
    await connection.execute(f"DROP TRIGGER {name} ON public.{table}")
    await connection.execute(f"DROP FUNCTION public.{name}_fn()")


async def test_bridge_atomicity(connection: asyncpg.Connection, teacher: int, submission: int) -> dict:
    baseline = await parent_snapshot(connection, submission)
    results: dict[str, str] = {}
    for suffix, table, timing, event, condition in (
        ("baseline_before", "submission_revisions", "BEFORE", "INSERT", ""),
        ("baseline_after", "submission_revisions", "AFTER", "INSERT", ""),
        ("pointer_before", "student_submissions", "BEFORE", "UPDATE", "current_revision_id"),
        ("pointer_after", "student_submissions", "AFTER", "UPDATE", "current_revision_id"),
    ):
        trigger = f"gate738h_inject_{suffix}"
        await install_raise_trigger(connection, table=table, timing=timing, event=event,
                                    name=trigger, condition=condition)
        code = None
        try:
            await connection.execute("""
                UPDATE student_submissions
                   SET status='REVIEWED',revision=2,content_json='after',submitted_at=now()
                 WHERE id=$1
            """, submission)
        except asyncpg.PostgresError as error:
            code = error.sqlstate
        await remove_raise_trigger(connection, table=table, name=trigger)
        after = await parent_snapshot(connection, submission)
        assert code == "P0001", {"probe": suffix, "sqlstate": code}
        assert after == baseline, {"probe": suffix, "before": baseline, "after": after}
        results[suffix] = f"PASS (SQLSTATE {code}; parent and revision rows rolled back)"

    # Allow a real compatibility write, then fail after the review bridge has
    # filled the legacy revision/provenance columns; no half-linked review may persist.
    await connection.execute("""
        UPDATE student_submissions
           SET status='REVIEWED',revision=2,content_json='after',submitted_at=now()
         WHERE id=$1
    """, submission)
    review_count = await connection.fetchval(
        "SELECT count(*) FROM submission_reviews WHERE submission_id=$1", submission,
    )
    trigger = "gate738h_inject_review_after"
    await install_raise_trigger(connection, table="submission_reviews", timing="AFTER",
                                event="INSERT", name=trigger)
    code = None
    try:
        await connection.execute("""
            INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
            VALUES($1,'gate738h-failure','REVIEWED',$2)
        """, submission, teacher)
    except asyncpg.PostgresError as error:
        code = error.sqlstate
    await remove_raise_trigger(connection, table="submission_reviews", name=trigger)
    count_after = await connection.fetchval(
        "SELECT count(*) FROM submission_reviews WHERE submission_id=$1", submission,
    )
    assert code == "P0001" and count_after == review_count
    results["review_after_bridge"] = f"PASS (SQLSTATE {code}; review count unchanged)"
    return results


async def inject_migration_boundaries(connection: asyncpg.Connection, database: str) -> dict:
    # A database-local event trigger fails after the first ALTER TABLE in 0030.
    # PostgreSQL/Alembic transactional DDL should leave both metadata and the
    # constraint catalog at the pre-migration state.
    await connection.execute("""
        CREATE FUNCTION public.gate738h_fail_contract_ddl() RETURNS event_trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected contract DDL failure'; END $$
    """)
    await connection.execute("""
        CREATE EVENT TRIGGER gate738h_fail_contract_ddl
        ON ddl_command_end WHEN TAG IN ('ALTER TABLE')
        EXECUTE FUNCTION public.gate738h_fail_contract_ddl()
    """)
    alembic(database, "20261003_0030", expect_failure=True)
    await connection.execute("DROP EVENT TRIGGER gate738h_fail_contract_ddl")
    await connection.execute("DROP FUNCTION public.gate738h_fail_contract_ddl()")
    head = await connection.fetchval("SELECT version_num FROM alembic_version")
    partial = await connection.fetchval("""
        SELECT count(*) FROM pg_constraint
         WHERE conname IN ('ck_submission_current_revision','ck_review_revision_id_not_null',
                           'ck_review_association_provenance_not_null')
    """)
    assert head == "20261003_0029" and partial == 0, {"head": head, "partial": partial}
    result = {"0030_mid_ddl": "PASS (metadata remains 0029; zero partial contract checks)"}

    await connection.execute("UPDATE submission_revision_backfill_state SET status='VALIDATED'")
    alembic(database, "20261003_0030")
    for suffix, timing in (("before", "BEFORE"), ("after", "AFTER")):
        function = f"gate738h_fail_fence_{suffix}_fn"
        trigger = f"gate738h_fail_fence_{suffix}"
        await connection.execute(f"""
            CREATE FUNCTION public.{function}() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'injected rollout fence failure' USING ERRCODE='P0001'; END $$
        """)
        await connection.execute(
            f"CREATE TRIGGER {trigger} {timing} UPDATE ON submission_revision_rollout_state "
            f"FOR EACH ROW EXECUTE FUNCTION public.{function}()"
        )
        alembic(database, "20261003_0031", expect_failure=True)
        head = await connection.fetchval("SELECT version_num FROM alembic_version")
        state = await connection.fetchval(
            "SELECT status FROM submission_revision_rollout_state WHERE singleton=true"
        )
        await connection.execute(f"DROP TRIGGER {trigger} ON submission_revision_rollout_state")
        await connection.execute(f"DROP FUNCTION public.{function}()")
        assert head == "20261003_0030" and state == "COMPATIBILITY", {
            "probe": suffix, "head": head, "rollout": state,
        }
        result[f"0031_fence_{suffix}"] = "PASS (metadata 0030; rollout remains COMPATIBILITY)"
    alembic(database, "20261003_0031")
    assert await connection.fetchval("SELECT version_num FROM alembic_version") == "20261003_0031"
    result["0031_success_after_removed_injection"] = "PASS"
    return result


async def main() -> None:
    admin = await asyncpg.connect(ADMIN_DSN)
    database = "gate738e_gate738h_failure_" + uuid4().hex
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
    finally:
        await admin.close()
    try:
        alembic(database, "20260921_0022")
        connection = await asyncpg.connect(dsn(database))
        try:
            teacher, submission = await seed(connection)
        finally:
            await connection.close()
        for revision in ("20261003_0027", "20261003_0028", "20261003_0029"):
            alembic(database, revision)
        connection = await asyncpg.connect(dsn(database))
        try:
            bridge = await test_bridge_atomicity(connection, teacher, submission)
            worker_env = os.environ.copy()
            worker_env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
            worker_env["GATE738E_DISPOSABLE"] = "1"
            worker = await asyncio.create_subprocess_exec(
                sys.executable, "-B", "scripts/backfill_submission_revisions.py",
                "--batch-size", "10", "--idle-timeout-seconds", "10",
                cwd=ROOT, env=worker_env, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await asyncio.wait_for(worker.communicate(), timeout=120)
            if worker.returncode:
                raise RuntimeError(stderr.decode(errors="replace")[-2500:])
            migration = await inject_migration_boundaries(connection, database)
            print({"bridge_atomicity": bridge, "migration_atomicity": migration,
                   "verdict": "PASS"})
        finally:
            await connection.close()
    finally:
        admin = await asyncpg.connect(ADMIN_DSN)
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        finally:
            await admin.close()


if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")
