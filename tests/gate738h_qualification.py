"""Retired historical Gate738H bridge, role, contract, and race harness.

This targets the pre-control-plane migration model and is not current release
qualification. The implementation is retained only as historical evidence and
helper code for already-recorded Gate738H runs. Use the explicit Gate738P
staged qualification after its environment prerequisites are satisfied.

Required environment:
  GATE738H_DISPOSABLE=1
  GATE738H_ADMIN_DSN=postgresql://postgres@127.0.0.1:<port>/postgres

The runner refuses non-loopback PostgreSQL and creates only uniquely named
gate738e_gate738h_* databases, satisfying both isolated harness guards. It
never prints the connection string or credentials.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from urllib.parse import quote, urlparse, urlunparse
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
ADMIN_DSN = os.environ["GATE738H_ADMIN_DSN"]
assert os.environ.get("GATE738H_DISPOSABLE") == "1"
_parsed = urlparse(ADMIN_DSN)
assert _parsed.scheme in {"postgres", "postgresql"}
assert _parsed.hostname in {"127.0.0.1", "localhost", "::1"}
assert _parsed.path.lstrip("/") == "postgres"


def db_dsn(db: str, *, sqlalchemy: bool = False, user: str | None = None) -> str:
    p = _parsed._replace(path=f"/{db}")
    if user:
        password = os.environ.get("GATE738H_RUNTIME_PASSWORD", "") if user == "app_runtime" else ""
        auth = f"{user}:{quote(password, safe='')}@" if password else f"{user}@"
        p = p._replace(netloc=f"{auth}{p.hostname}:{p.port}")
    raw = urlunparse(p)
    return raw.replace("postgresql://", "postgresql+asyncpg://", 1) if sqlalchemy else raw


def alembic(db: str, revision: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_dsn(db, sqlalchemy=True)
    p = subprocess.run(
        [sys.executable, "-B", "-m", "alembic", "upgrade", revision],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=240, check=False,
    )
    if p.returncode:
        raise RuntimeError(f"alembic {revision}: {p.stderr[-3500:]}")


async def seed(db: str, count: int) -> tuple[int, int, int]:
    c = await asyncpg.connect(db_dsn(db))
    try:
        teacher = await c.fetchval("INSERT INTO users(role) VALUES('TEACHER') RETURNING id")
        profile = await c.fetchval(
            "INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES($1,'gate738h') RETURNING id",
            teacher,
        )
        room = await c.fetchval(
            "INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id) "
            "VALUES('gate738h','gate738h',$1) RETURNING id", profile,
        )
        assignment = await c.fetchval(
            "INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) "
            "VALUES($1,$2,'gate738h','synthetic','PUBLISHED') RETURNING id", teacher, room,
        )
        first_user = await c.fetchval("SELECT coalesce(max(id),0)+1 FROM users")
        await c.execute(
            "INSERT INTO users(id,role) SELECT $1+g,'STUDENT' FROM generate_series(0,$2-1) g",
            first_user, count,
        )
        await c.execute("SELECT setval('users_id_seq', GREATEST((SELECT max(id) FROM users),1))")
        await c.execute("INSERT INTO student_profiles(student_id) SELECT $1+g FROM generate_series(0,$2-1) g", first_user, count)
        profile_first = await c.fetchval(
            "SELECT min(id) FROM student_profiles WHERE student_id >= $1", first_user,
        )
        await c.execute("""
            INSERT INTO student_submissions(assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
            SELECT $1,$2+g,'gate738h','SUBMITTED',1,'{"version":1}',now()
              FROM generate_series(0,$3-1) g
        """, assignment, profile_first, count)
        return int(teacher), int(assignment), int(profile_first + count - 1)
    finally:
        await c.close()


async def backfill_one(c: asyncpg.Connection, submission_id: int) -> bool:
    async with c.transaction():
        parent = await c.fetchrow("""
            SELECT id,tenant_id,revision,content_json,submitted_at
              FROM student_submissions
             WHERE id=$1 AND current_revision_id IS NULL
             FOR UPDATE SKIP LOCKED
        """, submission_id)
        if not parent:
            return False
        revision_id = await c.fetchval("""
            INSERT INTO submission_revisions(submission_id,tenant_id,revision_no,content_json,submitted_at,provenance)
            VALUES($1,$2,$3,$4,$5,'BASELINE_BACKFILL')
            ON CONFLICT(submission_id,revision_no) DO NOTHING RETURNING id
        """, parent["id"], parent["tenant_id"], parent["revision"], parent["content_json"], parent["submitted_at"])
        if revision_id is None:
            revision_id = await c.fetchval(
                "SELECT id FROM submission_revisions WHERE submission_id=$1 AND revision_no=$2",
                parent["id"], parent["revision"],
            )
        await c.execute("UPDATE student_submissions SET current_revision_id=$2 WHERE id=$1", submission_id, revision_id)
        await c.execute("""
            UPDATE submission_reviews SET submission_revision_id=$2,
                   association_provenance='MIGRATION_BASELINE_ONLY'
             WHERE submission_id=$1 AND submission_revision_id IS NULL
        """, submission_id, revision_id)
        return True


async def race_pair(db: str, submission_id: int, order: str) -> None:
    backfill = await asyncpg.connect(db_dsn(db))
    writer = await asyncpg.connect(db_dsn(db))
    try:
        if order == "backfill_first":
            tx = backfill.transaction()
            await tx.start()
            row = await backfill.fetchrow(
                "SELECT id,tenant_id,revision,content_json,submitted_at FROM student_submissions "
                "WHERE id=$1 AND current_revision_id IS NULL FOR UPDATE SKIP LOCKED", submission_id,
            )
            assert row is not None
            rev1 = await backfill.fetchval("""
                INSERT INTO submission_revisions(submission_id,tenant_id,revision_no,content_json,submitted_at,provenance)
                VALUES($1,$2,$3,$4,$5,'BASELINE_BACKFILL') RETURNING id
            """, row["id"], row["tenant_id"], row["revision"], row["content_json"], row["submitted_at"])
            await backfill.execute("UPDATE student_submissions SET current_revision_id=$2 WHERE id=$1", submission_id, rev1)
            update = asyncio.create_task(writer.execute("""
                UPDATE student_submissions SET status='REVIEWED',revision=2,
                    content_json='{"version":2}',submitted_at=now() WHERE id=$1
            """, submission_id))
            await asyncio.sleep(0)
            await tx.commit()
            await update
        else:
            tx = writer.transaction()
            await tx.start()
            await writer.execute("""
                UPDATE student_submissions SET status='REVIEWED',revision=2,
                    content_json='{"version":2}',submitted_at=now() WHERE id=$1
            """, submission_id)
            # A SKIP LOCKED pass must skip this row without waiting. The trigger
            # itself records v1 and v2 atomically in the writer transaction.
            assert not await backfill_one(backfill, submission_id)
            await tx.commit()
            assert not await backfill_one(backfill, submission_id)
        await writer.execute("""
            INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
            SELECT $1,'gate738h','REVIEWED',id FROM users WHERE role='TEACHER' ORDER BY id LIMIT 1
        """, submission_id)
        result = await backfill.fetchrow("""
            SELECT s.revision,s.content_json,s.current_revision_id,
                   r.revision_no,r.content_json AS current_snapshot,
                   (SELECT count(*) FROM submission_revisions x WHERE x.submission_id=s.id AND x.revision_no=1) AS baseline_count,
                   (SELECT count(*) FROM submission_revisions x WHERE x.submission_id=s.id) AS revision_count,
                   (SELECT count(*) FROM submission_reviews rv WHERE rv.submission_id=s.id AND rv.submission_revision_id IS NULL) AS unlinked_reviews
              FROM student_submissions s
              LEFT JOIN submission_revisions r ON r.id=s.current_revision_id
             WHERE s.id=$1
        """, submission_id)
        assert result["revision"] == result["revision_no"] == 2
        assert result["content_json"] == result["current_snapshot"] == '{"version":2}'
        assert result["baseline_count"] == 1 and result["revision_count"] == 2
        assert result["unlinked_reviews"] == 0
    finally:
        await backfill.close()
        await writer.close()


async def runtime_service_probe(db: str, teacher: int, assignment: int, student_profile: int) -> dict:
    # Assignment SELECT is a pre-existing runtime read grant; the migration
    # adds only the candidate-specific column grants for submission objects.
    bootstrap = await asyncpg.connect(db_dsn(db))
    await bootstrap.execute("GRANT SELECT ON public.assignments TO app_runtime")
    await bootstrap.close()
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.services.submission_revisions import bind_review, create_revision

    engine = create_async_engine(db_dsn(db, sqlalchemy=True, user="app_runtime"))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        await session.execute(text("SELECT set_config('app.tenant_id','gate738h',true)"))
        result = await create_revision(
            session, assignment_id=assignment, student_profile_id=student_profile,
            tenant_id="gate738h", idempotency_key=f"gate738h-runtime-{uuid4().hex}",
            content={"answer": "candidate-write"},
        )
        submission_id = result.submission.id
        revision_id = result.revision.id
    async with maker() as session, session.begin():
        await session.execute(text("SELECT set_config('app.tenant_id','gate738h',true)"))
        _, current = await bind_review(
            session, submission_id=submission_id, revision_id=revision_id,
            teacher_user_id=teacher, tenant_id="gate738h", review_status="REVIEWED",
            score=9, feedback="synthetic",
        )
        assert current
    async with maker() as session, session.begin():
        await session.execute(text("SELECT set_config('app.tenant_id','wrong-tenant',true)"))
        visible = await session.scalar(text(
            "SELECT count(*) FROM student_submissions WHERE id=:submission_id"
        ), {"submission_id": submission_id})
        changed = await session.execute(text(
            "UPDATE student_submissions SET revision=revision+1 WHERE id=:submission_id"
        ), {"submission_id": submission_id})
        assert visible == 0 and changed.rowcount == 0
    await engine.dispose()
    c = await asyncpg.connect(db_dsn(db))
    try:
        attrs = await c.fetchrow("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname='app_runtime'")
        assert not attrs["rolsuper"] and not attrs["rolbypassrls"]
        direct_delete = await c.fetchval("SELECT has_table_privilege('app_runtime','student_submissions','DELETE')")
        broad_parent_update = await c.fetchval("SELECT has_column_privilege('app_runtime','student_submissions','assignment_id','UPDATE')")
        broad_review_delete = await c.fetchval("SELECT has_table_privilege('app_runtime','submission_reviews','DELETE')")
        assert not direct_delete and not broad_parent_update and not broad_review_delete
        return {"role": dict(attrs), "candidate_service_write": "PASS", "candidate_review": "PASS",
                "table_delete": direct_delete, "unrelated_parent_column_update": broad_parent_update,
                "review_delete": broad_review_delete, "wrong_tenant_read": "DENIED",
                "wrong_tenant_update_rows": 0}
    finally:
        await c.close()


async def runtime_legacy_probe(db: str, teacher: int, *, expected_contract: bool) -> dict:
    """Exercise the prior runtime's raw parent/review SQL contract as app_runtime."""
    c = await asyncpg.connect(db_dsn(db, user="app_runtime"))
    try:
        await c.execute("SELECT set_config('app.tenant_id','gate738h',false)")
        parent_id = await c.fetchval("""
            SELECT s.id FROM student_submissions s
             WHERE s.status IN ('SUBMITTED','REVIEWED')
               AND NOT EXISTS (SELECT 1 FROM submission_reviews r WHERE r.submission_id=s.id)
             ORDER BY s.id LIMIT 1
        """)
        if parent_id is None:
            return {"legacy_sql": "NO_UNREVIEWED_PARENT_AVAILABLE"}
        before = await c.fetchrow(
            "SELECT revision,content_json,current_revision_id FROM student_submissions WHERE id=$1",
            parent_id,
        )
        try:
            await c.execute("""
                UPDATE student_submissions
                   SET status='REVIEWED',revision=revision+1,
                       content_json='legacy-compatibility-write',submitted_at=now()
                 WHERE id=$1
            """, parent_id)
            await c.execute("""
                INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
                VALUES($1,'gate738h','REVIEWED',$2)
            """, parent_id, teacher)
        except asyncpg.PostgresError as error:
            if not expected_contract or error.sqlstate != "55000":
                raise
            after = await c.fetchrow(
                "SELECT revision,content_json,current_revision_id FROM student_submissions WHERE id=$1",
                parent_id,
            )
            assert dict(after) == dict(before)
            assert await c.fetchval(
                "SELECT count(*) FROM submission_reviews WHERE submission_id=$1", parent_id,
            ) == 0
            return {"legacy_parent_and_review": "DENIED_AT_CONTRACT", "sqlstate": error.sqlstate,
                    "parent_unchanged": True, "review_count_unchanged": True}
        if expected_contract:
            raise AssertionError("legacy runtime SQL unexpectedly succeeded after contraction")
        state = await c.fetchrow("""
            SELECT s.revision,s.content_json,r.revision_no,
                   (SELECT count(*) FROM submission_revisions x
                     WHERE x.submission_id=s.id AND x.revision_no=$2) AS current_count,
                   (SELECT count(*) FROM submission_reviews rv WHERE rv.submission_id=s.id
                     AND rv.submission_revision_id=s.current_revision_id
                     AND rv.association_provenance='LEGACY_COMPAT') AS linked_review_count
              FROM student_submissions s JOIN submission_revisions r ON r.id=s.current_revision_id
             WHERE s.id=$1
        """, parent_id, before["revision"] + 1)
        assert state["revision"] == state["revision_no"] == before["revision"] + 1
        assert state["content_json"] == "legacy-compatibility-write"
        assert state["current_count"] == state["linked_review_count"] == 1
        return {"legacy_parent_and_review": "ACCEPTED_AND_BRIDGED", "integrity": "PASS"}
    finally:
        await c.close()


async def failure_atomicity_probe() -> dict:
    admin = await asyncpg.connect(ADMIN_DSN)
    db = "gate738e_gate738h_failure_" + uuid4().hex
    try:
        await admin.execute(f'CREATE DATABASE "{db}"')
        alembic(db, "20260921_0022")
        await seed(db, 1)
        for rev in ("20261003_0027", "20261003_0028", "20261003_0029"):
            alembic(db, rev)
        env = os.environ.copy()
        env["DATABASE_URL"] = db_dsn(db, sqlalchemy=True)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-B", "-m", "alembic", "upgrade", "20261003_0030",
            cwd=ROOT, env=env, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        assert proc.returncode != 0, "0030 unexpectedly contracted a PENDING backfill"
        c = await asyncpg.connect(db_dsn(db))
        try:
            head = await c.fetchval("SELECT version_num FROM alembic_version")
            partial = await c.fetchval("""
                SELECT count(*) FROM pg_constraint
                 WHERE conname IN ('ck_submission_current_revision',
                                   'ck_review_revision_id_not_null',
                                   'ck_review_association_provenance_not_null')
            """)
            state = await c.fetchval("SELECT status FROM submission_revision_backfill_state WHERE singleton=true")
            assert head == "20261003_0029" and partial == 0 and state == "PENDING"
        finally:
            await c.close()
        return {"contract_refused_before_validation": True, "alembic_head_after_failure": head,
                "partial_contract_constraints": partial, "backfill_state": state,
                "failure_excerpt": stderr.decode(errors="replace")[-500:]}
    finally:
        # This database name was generated above and is exclusively Gate-owned.
        await admin.execute(f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE)')
        await admin.close()


async def contract_probe(db: str, teacher: int, assignment: int, student_profile: int) -> dict:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.services.submission_revisions import create_revision

    # In-flight compatibility writer holds the shared rollout row; contract
    # transition must wait for it, then atomically fence a queued legacy write.
    c = await asyncpg.connect(db_dsn(db))
    parent_id = await c.fetchval("SELECT id FROM student_submissions ORDER BY id LIMIT 1")
    assert parent_id is not None, "synthetic parent missing before contract probe"
    tx = c.transaction()
    await tx.start()
    await c.execute("SELECT status FROM submission_revision_rollout_state WHERE singleton=true FOR SHARE")
    fence_env = os.environ.copy()
    fence_env["DATABASE_URL"] = db_dsn(db, sqlalchemy=True)
    fence = await asyncio.create_subprocess_exec(
        sys.executable, "-B", "-m", "alembic", "upgrade", "20261003_0031",
        cwd=ROOT, env=fence_env, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await asyncio.sleep(.05)
    assert fence.returncode is None, "contract migration did not wait for an in-flight compatibility transaction"
    await tx.commit()
    _fence_stdout, fence_stderr = await asyncio.wait_for(fence.communicate(), timeout=60)
    if fence.returncode:
        raise RuntimeError(f"0031 fence migration failed: {fence_stderr.decode(errors='replace')[-2000:]}")

    # Contracted old writer must fail atomically with the explicit guard.
    before = await c.fetchrow("SELECT revision,content_json,current_revision_id FROM student_submissions WHERE id=$1", parent_id)
    legacy_error = None
    try:
        await c.execute("UPDATE student_submissions SET revision=revision+1,content_json='legacy-after-contract' WHERE id=$1", parent_id)
    except asyncpg.PostgresError as exc:
        legacy_error = exc.sqlstate
    assert legacy_error == "55000"
    after = await c.fetchrow("SELECT revision,content_json,current_revision_id FROM student_submissions WHERE id=$1", parent_id)
    assert dict(before) == dict(after)
    reviews_before = await c.fetchval("SELECT count(*) FROM submission_reviews WHERE submission_id=$1", parent_id)
    review_error = None
    try:
        await c.execute("INSERT INTO submission_reviews(submission_id,tenant_id,review_status) VALUES($1,'gate738h','REVIEWED')", parent_id)
    except asyncpg.PostgresError as exc:
        review_error = exc.sqlstate
    assert review_error == "55000"
    review_count = await c.fetchval("SELECT count(*) FROM submission_reviews WHERE submission_id=$1", parent_id)
    assert review_count == reviews_before
    await c.close()

    # Candidate runtime's exact revision write remains accepted after the fence.
    engine = create_async_engine(db_dsn(db, sqlalchemy=True, user="app_runtime"))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        await session.execute(text("SELECT set_config('app.tenant_id','gate738h',true)"))
        result = await create_revision(
            session, assignment_id=assignment, student_profile_id=student_profile,
            tenant_id="gate738h", idempotency_key="gate738h-runtime-post-contract",
            content={"answer": "post-contract"},
        )
        candidate_id = result.submission.id
    await engine.dispose()
    return {"fence_waited_for_inflight_writer": True, "legacy_parent_sqlstate": legacy_error,
            "legacy_parent_atomic": dict(before) == dict(after), "legacy_review_sqlstate": review_error,
            "legacy_review_rows_after_failure": review_count,
            "candidate_write_after_contract": candidate_id is not None}


async def main() -> None:
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        role = await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname='app_runtime'")
        if not role:
            await admin.execute("CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS")
        runtime_password = uuid4().hex
        alter = await admin.fetchval(
            "SELECT format('ALTER ROLE app_runtime PASSWORD %L', $1::text)", runtime_password
        )
        await admin.execute(alter)
        os.environ["GATE738H_RUNTIME_PASSWORD"] = runtime_password
        db = "gate738e_gate738h_" + uuid4().hex
        await admin.execute(f'CREATE DATABASE "{db}"')
    finally:
        await admin.close()

    alembic(db, "20260921_0022")
    teacher, assignment, student_profile = await seed(db, 400)
    for rev in ("20261003_0027", "20261003_0028", "20261003_0029"):
        alembic(db, rev)

    c = await asyncpg.connect(db_dsn(db))
    rows = await c.fetch("SELECT id FROM student_submissions ORDER BY id LIMIT 200")
    await c.close()
    for i, row in enumerate(rows):
        await race_pair(db, row["id"], "backfill_first" if i % 2 == 0 else "writer_first")

    # The remaining unprocessed rows are completed through the real resumable worker.
    env = os.environ.copy()
    env["DATABASE_URL"] = db_dsn(db, sqlalchemy=True)
    env["GATE738E_DISPOSABLE"] = "1"
    worker = await asyncio.create_subprocess_exec(
        sys.executable, "-B", "scripts/backfill_submission_revisions.py", "--batch-size", "75",
        "--idle-timeout-seconds", "10", cwd=ROOT, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, worker_stderr = await asyncio.wait_for(worker.communicate(), timeout=240)
    if worker.returncode:
        raise RuntimeError(worker_stderr.decode(errors="replace")[-3500:])
    role_results = await runtime_service_probe(db, teacher, assignment, student_profile)
    legacy_0029 = await runtime_legacy_probe(db, teacher, expected_contract=False)

    # 0030 lock qualification while short readers and representative writers run.
    c = await asyncpg.connect(db_dsn(db))
    stop = asyncio.Event()
    reader_errors: list[str] = []
    writer_errors: list[str] = []

    async def reader_loop() -> None:
        while not stop.is_set():
            try:
                await c.fetchval("SELECT count(*) FROM student_submissions")
            except asyncpg.PostgresError as exc:  # pragma: no cover - recorded on failure
                reader_errors.append(type(exc).__name__)
            await asyncio.sleep(.005)

    async def writer_loop() -> None:
        wc = await asyncpg.connect(db_dsn(db))
        try:
            # A finite writer burst overlaps 0030 without continuously queuing
            # new relation locks behind its ACCESS EXCLUSIVE request.
            for _ in range(30):
                if stop.is_set():
                    break
                try:
                    await wc.execute("UPDATE student_submissions SET updated_at=now() WHERE id=$1", rows[0]["id"])
                except asyncpg.PostgresError as exc:  # pragma: no cover - recorded on failure
                    writer_errors.append(type(exc).__name__)
                await asyncio.sleep(.005)
        finally:
            await wc.close()

    readers = asyncio.create_task(reader_loop())
    writers = asyncio.create_task(writer_loop())
    await asyncio.sleep(.05)
    alembic(db, "20261003_0030")
    await asyncio.sleep(.05)
    stop.set()
    await asyncio.gather(readers, writers)
    assert not reader_errors and not writer_errors, {"reader_errors": reader_errors, "writer_errors": writer_errors}
    await c.close()
    candidate_0030 = await runtime_service_probe(db, teacher, assignment, student_profile)
    legacy_0030 = await runtime_legacy_probe(db, teacher, expected_contract=False)
    lock_results = {"short_reader_failures": len(reader_errors), "writer_failures": len(writer_errors),
                    "contract_0030": "PASS", "contract_elapsed_ms": "captured-by-runner"}

    contract_results = await contract_probe(db, teacher, assignment, student_profile)
    legacy_0031 = await runtime_legacy_probe(db, teacher, expected_contract=True)
    atomicity = await failure_atomicity_probe()
    c = await asyncpg.connect(db_dsn(db))
    integrity = await c.fetchrow("""
        SELECT (SELECT count(*) FROM student_submissions s WHERE s.status IN ('SUBMITTED','REVIEWED')
                 AND NOT EXISTS (SELECT 1 FROM submission_revisions r WHERE r.id=s.current_revision_id
                     AND r.submission_id=s.id AND r.tenant_id=s.tenant_id AND r.revision_no=s.revision)) AS missing_current,
               (SELECT count(*) FROM submission_reviews r WHERE r.submission_revision_id IS NULL
                    OR NOT EXISTS (SELECT 1 FROM submission_revisions x WHERE x.id=r.submission_revision_id
                        AND x.submission_id=r.submission_id AND x.tenant_id=r.tenant_id)) AS invalid_reviews,
               (SELECT status FROM submission_revision_rollout_state WHERE singleton=true) AS rollout_status,
               (SELECT count(*) FROM submission_revisions WHERE submission_id IN (SELECT id FROM student_submissions)) AS revision_count
    """)
    assert integrity["missing_current"] == 0 and integrity["invalid_reviews"] == 0
    assert integrity["rollout_status"] == "CONTRACTED"
    await c.close()
    print(json.dumps({"database": db, "synthetic_parents": len(rows),
                      "race_matrix": {"backfill_first": 100, "writer_first": 100,
                                      "baseline_and_current_revision_integrity": "PASS"},
                      "runtime_role": role_results,
                      "compatibility_matrix": {
                          "schema_0029_compatibility_old_sql": legacy_0029,
                          "schema_0030_compatibility_old_sql": legacy_0030,
                          "schema_0030_candidate_runtime": candidate_0030["candidate_service_write"],
                          "schema_0031_contracted_old_sql": legacy_0031,
                          "schema_0031_candidate_runtime": contract_results["candidate_write_after_contract"],
                      },
                      "lock_matrix": lock_results,
                      "contract": contract_results, "failure_atomicity": atomicity,
                      "final_integrity": dict(integrity),
                      "head": "20261003_0031", "verdict": "PASS"}, default=str, indent=2))


if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")
