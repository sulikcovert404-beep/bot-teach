"""Pure request validation; PostgreSQL lifecycle qualification is separate."""

import asyncio
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.submission_revisions import (
    SubmissionRevisionConflict,
    SubmissionRevisionError,
    bind_review,
    create_revision,
    encode_submission,
    read_feedback,
    validate_idempotency_key,
)


def test_fingerprint_is_stable_for_object_key_order():
    first = {"answer": {"b": 2, "a": 1}, "text": "پاسخ"}
    second = {"text": "پاسخ", "answer": {"a": 1, "b": 2}}
    assert encode_submission(first) == encode_submission(second)
    assert encode_submission(first)[1] != encode_submission({"answer": 3})[1]


@pytest.mark.parametrize("value", ["", " key", "key ", "a\nb", "a\x00b", "x" * 129, None])
def test_invalid_keys_are_rejected_without_normalization(value):
    with pytest.raises(SubmissionRevisionError):
        validate_idempotency_key(value)


def test_key_boundaries_are_preserved():
    assert validate_idempotency_key("a") == "a"
    assert validate_idempotency_key("x" * 128) == "x" * 128


@pytest.mark.parametrize("content", [[], {"n": float("nan")}, {"n": float("inf")}, {"x": object()}])
def test_invalid_content_reports_no_payload(content):
    with pytest.raises(SubmissionRevisionError) as error:
        encode_submission(content)
    assert str(error.value) in {
        "submission content must be an object",
        "submission content must be valid JSON",
    }


def test_postgresql_revision_feedback_lifecycle():
    port = os.environ.get("GATE738E_LOCAL_PG_PORT")
    if not port:
        pytest.skip("Explicit disposable Gate738E PostgreSQL port required")
    assert port.isdigit() and 1 <= int(port) <= 65535

    migration_environment = os.environ.copy()
    migration_environment["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{port}/gate738e_test"
    migration = subprocess.run(
        [sys.executable, "-B", "-m", "alembic", "upgrade", "20261003_0031"],
        env=migration_environment, capture_output=True, text=True, timeout=60, check=False,
    )
    assert migration.returncode == 0, migration.stderr

    async def scenario():
        engine = create_async_engine(
            f"postgresql+asyncpg://gate738e@127.0.0.1:{port}/gate738e_test"
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        tenant = "gate738e-" + uuid4().hex
        try:
            async with factory() as session, session.begin():
                assert await session.scalar(text("SELECT current_database()")) == "gate738e_test"
                assert await session.scalar(text("SELECT current_user")) == "gate738e"
                teacher = await session.scalar(text("INSERT INTO users(role) VALUES ('TEACHER') RETURNING id"))
                student = await session.scalar(text("INSERT INTO users(role) VALUES ('STUDENT') RETURNING id"))
                profile = await session.scalar(text("INSERT INTO student_profiles(student_id) VALUES (:id) RETURNING id"), {"id": student})
                tp = await session.scalar(text("INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES (:id,:tenant) RETURNING id"), {"id": teacher, "tenant": tenant})
                classroom = await session.scalar(text("INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id) VALUES (:tenant,:tenant,:id) RETURNING id"), {"id": tp, "tenant": tenant})
                assignment = await session.scalar(text("INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) VALUES (:teacher,:classroom,:tenant,'Gate738E synthetic','PUBLISHED') RETURNING id"), {"teacher": teacher, "classroom": classroom, "tenant": tenant})
            async with factory() as session, session.begin():
                first = await create_revision(session, assignment_id=assignment, student_profile_id=profile, tenant_id=tenant, idempotency_key="first", content={"answer": 1})
                parent_id, first_id = first.submission.id, first.revision.id
                assert not first.replayed
            async with factory() as session, session.begin():
                replay = await create_revision(session, assignment_id=assignment, student_profile_id=profile, tenant_id=tenant, idempotency_key="first", content={"answer": 1})
                assert replay.replayed and replay.revision.id == first_id
                with pytest.raises(SubmissionRevisionConflict):
                    await create_revision(session, assignment_id=assignment, student_profile_id=profile, tenant_id=tenant, idempotency_key="first", content={"answer": 2})
                _, current = await bind_review(session, submission_id=parent_id, revision_id=first_id, teacher_user_id=teacher, tenant_id=tenant, review_status="REVIEWED", score=9, feedback="synthetic feedback")
                assert current
                feedback = await read_feedback(session, submission_id=parent_id, student_profile_id=profile, tenant_id=tenant)
                assert feedback["status"] == "REVIEWED"
                assert feedback["revisions"][0]["review"]["feedback"] == "synthetic feedback"
            async with factory() as session, session.begin():
                second = await create_revision(session, assignment_id=assignment, student_profile_id=profile, tenant_id=tenant, idempotency_key="second", content={"answer": 2})
                assert second.revision.revision_no == 2
                feedback = await read_feedback(session, submission_id=parent_id, student_profile_id=profile, tenant_id=tenant)
                assert feedback["status"] == "SUBMITTED"
                assert not feedback["revisions"][0]["is_current"]
                assert feedback["revisions"][0]["review"] is not None
                assert feedback["revisions"][1]["is_current"]
                assert feedback["revisions"][1]["review"] is None
                for owner, scope in [(profile + 100000, tenant), (profile, "other-tenant")]:
                    with pytest.raises(SubmissionRevisionError):
                        await read_feedback(session, submission_id=parent_id, student_profile_id=owner, tenant_id=scope)
                _, current = await bind_review(session, submission_id=parent_id, revision_id=first_id, teacher_user_id=teacher, tenant_id=tenant, review_status="REVIEWED", score=8, feedback="historical review")
                assert not current
                feedback = await read_feedback(session, submission_id=parent_id, student_profile_id=profile, tenant_id=tenant)
                assert feedback["status"] == "SUBMITTED"
                with pytest.raises(SubmissionRevisionError):
                    await bind_review(session, submission_id=parent_id, revision_id=first_id, teacher_user_id=teacher + 100000, tenant_id=tenant, review_status="REVIEWED", score=0, feedback=None)

            async def concurrent_submit(key, target_assignment=assignment):
                async with factory() as session, session.begin():
                    result = await create_revision(session, assignment_id=target_assignment, student_profile_id=profile, tenant_id=tenant, idempotency_key=key, content={"answer": 3})
                    return result.revision.id, result.revision.revision_no, result.replayed

            duplicate_results = await asyncio.wait_for(
                asyncio.gather(concurrent_submit("concurrent"), concurrent_submit("concurrent")),
                timeout=15,
            )
            assert duplicate_results[0][:2] == duplicate_results[1][:2]
            assert sorted(result[2] for result in duplicate_results) == [False, True]
            distinct_results = await asyncio.wait_for(
                asyncio.gather(concurrent_submit("four"), concurrent_submit("five")),
                timeout=15,
            )
            assert sorted(result[1] for result in distinct_results) == [4, 5]
            assert all(not result[2] for result in distinct_results)
            # The role exists only inside this disposable test database cluster.
            # Create and roll it back with the qualification transaction.
            async with factory() as session, session.begin():
                await session.execute(text("CREATE ROLE gate738e_rls_probe NOLOGIN NOSUPERUSER NOBYPASSRLS"))
                await session.execute(text("GRANT SELECT ON submission_revisions, student_submissions, submission_reviews TO gate738e_rls_probe"))
                await session.execute(text("GRANT INSERT ON submission_revisions TO gate738e_rls_probe"))
                await session.execute(text("GRANT UPDATE ON student_submissions TO gate738e_rls_probe"))
                await session.execute(text("GRANT USAGE ON SEQUENCE submission_revisions_id_seq TO gate738e_rls_probe"))
                await session.execute(text("SET LOCAL ROLE gate738e_rls_probe"))
                assert not await session.scalar(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"))
                assert await session.scalar(text("SELECT count(*) FROM submission_revisions")) == 0
                await session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": tenant})
                assert await session.scalar(text("SELECT count(*) FROM submission_revisions")) == 5
                feedback = await read_feedback(session, submission_id=parent_id, student_profile_id=profile, tenant_id=tenant)
                assert len(feedback["revisions"]) == 5
                result = await create_revision(session, assignment_id=assignment, student_profile_id=profile, tenant_id=tenant, idempotency_key="runtime", content={"answer": 6})
                assert result.revision.revision_no == 6
                await session.execute(text("SELECT set_config('app.tenant_id', 'unrelated-tenant', true)"))
                assert await session.scalar(text("SELECT count(*) FROM submission_revisions")) == 0
                with pytest.raises(DBAPIError) as denied:
                    async with session.begin_nested():
                        await session.execute(text("INSERT INTO submission_revisions(submission_id,tenant_id,revision_no,provenance) VALUES (:parent,:tenant,7,'BASELINE_BACKFILL')"), {"parent": parent_id, "tenant": tenant})
                assert denied.value.orig.sqlstate == "42501"
                with pytest.raises(SubmissionRevisionError):
                    await read_feedback(session, submission_id=parent_id, student_profile_id=profile, tenant_id=tenant)
                await session.rollback()
            async with factory() as session, session.begin():
                fresh_assignment = await session.scalar(text("INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) VALUES (:teacher,:classroom,:tenant,'Gate738E race','PUBLISHED') RETURNING id"), {"teacher": teacher, "classroom": classroom, "tenant": tenant})
            initial_race = await asyncio.wait_for(
                asyncio.gather(
                    concurrent_submit("initial-race", fresh_assignment),
                    concurrent_submit("initial-race", fresh_assignment),
                ), timeout=15,
            )
            assert initial_race[0][:2] == initial_race[1][:2]
            assert initial_race[0][1] == 1
            assert sorted(result[2] for result in initial_race) == [False, True]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
