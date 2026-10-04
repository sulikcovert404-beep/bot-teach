"""Gate738E staged migration rehearsal on an explicitly disposable PostgreSQL."""

import asyncio
import os
import subprocess
import sys
from uuid import uuid4

import asyncpg
import pytest


@pytest.mark.parametrize("invalid_review", [False, True])
def test_staged_legacy_upgrade(invalid_review):
    port = os.environ.get("GATE738E_LOCAL_PG_PORT")
    if not port:
        pytest.skip("Explicit Gate738E disposable PostgreSQL port required")
    assert port.isdigit() and 1 <= int(port) <= 65535
    database = "gate738e_" + uuid4().hex

    async def connect(name):
        return await asyncpg.connect(host="127.0.0.1", port=int(port), user="gate738e", database=name)

    def alembic(revision):
        environment = os.environ.copy()
        environment["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{port}/{database}"
        return subprocess.run(
            [sys.executable, "-B", "-m", "alembic", "upgrade", revision],
            env=environment, capture_output=True, text=True, timeout=120, check=False,
        )

    def backfill(max_batches=None):
        environment = os.environ.copy()
        environment["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{port}/{database}"
        environment["GATE738E_DISPOSABLE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", "scripts/backfill_submission_revisions.py",
             "--batch-size", "1", "--idle-timeout-seconds", "1"]
            + (["--max-batches", str(max_batches)] if max_batches else []),
            env=environment, capture_output=True, text=True, timeout=120, check=False,
        )

    async def create_database():
        connection = await connect("gate738e_test")
        try:
            assert await connection.fetchval("SELECT current_user") == "gate738e"
            await connection.execute(f'CREATE DATABASE "{database}"')
        finally:
            await connection.close()

    async def seed():
        connection = await connect(database)
        try:
            await connection.execute("""
                INSERT INTO users(id,role) VALUES (1,'TEACHER'),(2,'STUDENT'),(3,'STUDENT'),(4,'STUDENT'),(5,'STUDENT');
                INSERT INTO teacher_profiles(id,teacher_id,tenant_id) VALUES (1,1,'legacy');
                INSERT INTO student_profiles(id,student_id) VALUES (1,2),(2,3),(3,4),(4,5);
                INSERT INTO classrooms(id,classroom_key,tenant_id,teacher_profile_id) VALUES (1,'legacy','legacy',1);
                INSERT INTO assignments(id,teacher_id,classroom_id,tenant_id,title)
                    VALUES (1,1,1,'legacy','synthetic');
                INSERT INTO student_submissions(id,assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
                VALUES (1,1,1,'legacy','REVIEWED',4,'{"answer":42}',now()),
                       (2,1,2,'legacy','NOT_SUBMITTED',1,NULL,NULL),
                       (3,1,3,'legacy','SUBMITTED',2,'{"answer":"second"}',now());
                INSERT INTO submission_reviews(submission_id,tenant_id,review_status,score,teacher_feedback,reviewed_by)
                VALUES (1,'legacy','REVIEWED',8,'synthetic feedback',1);
            """)
            if invalid_review:
                await connection.execute(
                    "INSERT INTO submission_reviews(submission_id,tenant_id) VALUES (2,'legacy')"
                )
        finally:
            await connection.close()

    async def verify_invalid_stopped_at_expand():
        connection = await connect(database)
        try:
            assert await connection.fetchval("SELECT version_num FROM alembic_version") == "20261003_0029"
            assert await connection.fetchval("SELECT status FROM submission_revision_backfill_state") == "RUNNING"
            assert await connection.fetchval("SELECT count(*) FROM student_submissions") == 3
            assert await connection.fetchval("SELECT count(*) FROM submission_reviews") == 2
            assert await connection.fetchval("SELECT count(*) FROM submission_revisions") == 2
        finally:
            await connection.close()

    async def verify_valid_contract():
        connection = await connect(database)
        try:
            assert await connection.fetchval("SELECT version_num FROM alembic_version") == "20261003_0031"
            assert await connection.fetchval("SELECT status FROM submission_revision_backfill_state") == "CONTRACTED"
            rows = await connection.fetch("""
                SELECT s.id AS submission_id,s.current_revision_id,r.id AS revision_id,r.revision_no,
                       r.content_json,r.submit_idempotency_key,r.request_fingerprint,r.provenance
                  FROM student_submissions s
                  JOIN submission_revisions r ON r.id=s.current_revision_id
                 ORDER BY s.id
            """)
            assert len(rows) == 3
            baseline = next(row for row in rows if row["submission_id"] == 1)
            assert baseline["current_revision_id"] == baseline["revision_id"]
            assert baseline["revision_no"] == 4
            assert baseline["content_json"] == '{"answer":42}'
            assert baseline["submit_idempotency_key"] is None
            assert baseline["request_fingerprint"] is None
            assert baseline["provenance"] == "BASELINE_BACKFILL"
            assert next(row for row in rows if row["submission_id"] == 3)["provenance"] == "BASELINE_BACKFILL"
            assert next(row for row in rows if row["submission_id"] == 4)["provenance"] == "LEGACY_COMPAT"
            review = await connection.fetchrow("""
                SELECT submission_revision_id,association_provenance,teacher_feedback
                  FROM submission_reviews WHERE submission_id=1
            """)
            assert review["submission_revision_id"] == rows[0]["revision_id"]
            assert review["association_provenance"] == "MIGRATION_BASELINE_ONLY"
            assert review["teacher_feedback"] == "synthetic feedback"
            assert await connection.fetchval("SELECT count(*) FROM submission_revisions") == 3
            # The exact revision and review composite FKs reject cross-parent links.
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE student_submissions SET current_revision_id=999999 WHERE id=1"
                    )
            with pytest.raises(asyncpg.UniqueViolationError):
                async with connection.transaction():
                    await connection.execute("""
                        INSERT INTO submission_revisions
                            (submission_id,tenant_id,revision_no,provenance)
                        VALUES (1,'legacy',4,'BASELINE_BACKFILL')
                    """)
            for statement in [
                "UPDATE submission_revisions SET content_json='{}' WHERE submission_id=1",
                "DELETE FROM submission_revisions WHERE submission_id=1",
            ]:
                with pytest.raises(asyncpg.ObjectNotInPrerequisiteStateError) as immutable:
                    async with connection.transaction():
                        await connection.execute(statement)
                assert immutable.value.sqlstate == "55000"
        finally:
            await connection.close()

    asyncio.run(create_database())
    before = alembic("20260921_0022")
    assert before.returncode == 0, before.stderr
    asyncio.run(seed())
    expanded = alembic("20261003_0029")
    assert expanded.returncode == 0, expanded.stderr
    if not invalid_review:
        async def exercise_legacy_compatibility():
            connection = await connect(database)
            try:
                await connection.execute("""
                    INSERT INTO student_submissions
                        (id,assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
                        VALUES (4,1,4,'legacy','SUBMITTED',1,'{\"answer\":\"legacy writer\"}',now())
                """)
                assert await connection.fetchval(
                    "SELECT count(*) FROM submission_revisions WHERE submission_id=4 AND provenance='LEGACY_COMPAT'"
                ) == 1
                await connection.execute("""
                    INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
                    VALUES (4,'legacy','REVIEWED',1)
                """)
                assert await connection.fetchval(
                    "SELECT association_provenance FROM submission_reviews WHERE submission_id=4"
                ) == "LEGACY_COMPAT"
            finally:
                await connection.close()
        asyncio.run(exercise_legacy_compatibility())
    result = backfill(max_batches=1 if not invalid_review else None)
    if invalid_review:
        assert result.returncode != 0
        assert "DO NOT CONTRACT" in result.stderr
        asyncio.run(verify_invalid_stopped_at_expand())
        contract = alembic("20261003_0031")
        assert contract.returncode != 0
        return

    assert result.returncode != 0 and "BACKFILL_PAUSED" in result.stderr
    async def verify_checkpoint():
        connection = await connect(database)
        try:
            state = await connection.fetchrow("SELECT status,processed_submissions FROM submission_revision_backfill_state")
            assert state["status"] == "RUNNING"
            assert state["processed_submissions"] == 1
        finally:
            await connection.close()
    asyncio.run(verify_checkpoint())
    result = backfill()
    assert result.returncode == 0, result.stderr
    assert "errors=0" in result.stdout
    contract = alembic("20261003_0031")
    assert contract.returncode == 0, contract.stderr
    asyncio.run(verify_valid_contract())
