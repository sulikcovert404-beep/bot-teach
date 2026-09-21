import asyncio
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import AuditLog, ProvisioningIdempotencyKey, SchoolTenant, StudentProfile, User
from app.services.test_identity_provisioning import ProvisioningDenied, provision_test_identity


@pytest.mark.asyncio
async def test_provision_student_is_atomic_and_idempotent() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        owner = User(telegram_user_id=900, role="SUPER_ADMIN")
        session.add(owner)
        await session.flush()
        await session.commit()
        first = await provision_test_identity(
            session,
            actor_user_id=owner.id,
            provider="telegram",
            subject="901",
            username="pilot-student",
            role="STUDENT",
            tenant_id=None,
            audit_reason="controlled test",
            idempotency_key="pilot-1",
        )
        second = await provision_test_identity(
            session,
            actor_user_id=owner.id,
            provider="telegram",
            subject="901",
            username="pilot-student",
            role="STUDENT",
            tenant_id=None,
            audit_reason="controlled test retry",
            idempotency_key="pilot-1-retry",
        )
        assert first.status == "CREATED"
        assert second.status == "EXISTING"
        assert first.user_id == second.user_id
        assert await session.scalar(select(StudentProfile).where(StudentProfile.student_id == first.user_id))
        assert (await session.scalars(select(User))).all().__len__() == 2
        assert len((await session.scalars(select(AuditLog))).all()) == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_teacher_requires_existing_tenant_and_rejects_owner_role() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        owner = User(telegram_user_id=910, role="SUPER_ADMIN")
        session.add(owner)
        await session.flush()
        owner_id = owner.id
        await session.commit()
        with pytest.raises(ProvisioningDenied, match="tenant not found"):
            await provision_test_identity(
                session,
                actor_user_id=owner_id,
                provider="telegram",
                subject="911",
                username="pilot-teacher",
                role="TEACHER",
                tenant_id="missing",
                audit_reason="controlled test",
                idempotency_key="pilot-2",
            )
        session.add(SchoolTenant(tenant_id="school-a", school_name="A"))
        await session.commit()
        with pytest.raises(ProvisioningDenied, match="role is not provisionable"):
            await provision_test_identity(
                session,
                actor_user_id=owner_id,
                provider="telegram",
                subject="912",
                username="pilot-owner",
                role="SUPER_ADMIN",
                tenant_id="school-a",
                audit_reason="controlled test",
                idempotency_key="pilot-3",
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_persisted_key_replays_and_rejects_fingerprint_conflict() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        owner = User(telegram_user_id=920, role="SUPER_ADMIN")
        session.add(owner)
        await session.flush()
        await session.commit()
        kwargs = {"actor_user_id": owner.id, "provider": "telegram", "subject": "921",
                  "username": "replay", "role": "STUDENT", "tenant_id": None,
                  "audit_reason": "same request", "idempotency_key": "stable-key"}
        first = await provision_test_identity(session, **kwargs)
        replay = await provision_test_identity(session, **kwargs)
        assert first.status == "CREATED"
        assert replay.status == "REPLAY"
        assert replay.user_id == first.user_id
        record = await session.scalar(select(ProvisioningIdempotencyKey).where(
            ProvisioningIdempotencyKey.idempotency_key == "stable-key"
        ))
        assert record is not None and record.correlation_id
        await session.rollback()
        with pytest.raises(ProvisioningDenied, match="conflicts"):
            await provision_test_identity(session, **{**kwargs, "subject": "922"})
    await engine.dispose()


@pytest.mark.asyncio
async def test_same_key_replay_has_one_identity_sqlite() -> None:
    import tempfile
    from pathlib import Path

    db_path = Path(tempfile.mktemp(suffix=".sqlite"))
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        owner = User(telegram_user_id=925, role="SUPER_ADMIN")
        session.add(owner)
        await session.flush()
        owner_id = owner.id
        await session.commit()

    async with sessions() as first_session:
        first = await provision_test_identity(
            first_session, actor_user_id=owner_id, provider="telegram", subject="926",
            username="concurrent", role="STUDENT", tenant_id=None,
            audit_reason="sqlite replay qualification", idempotency_key="concurrent-key",
        )
    async with sessions() as replay_session:
        replay = await provision_test_identity(
            replay_session, actor_user_id=owner_id, provider="telegram", subject="926",
            username="concurrent", role="STUDENT", tenant_id=None,
            audit_reason="sqlite replay qualification", idempotency_key="concurrent-key",
        )
    assert first.status == "CREATED"
    assert replay.status == "REPLAY"
    assert replay.user_id == first.user_id
    async with sessions() as session:
        assert len((await session.scalars(select(User))).all()) == 2
    await engine.dispose()
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_concurrent_conflicting_key_allows_one_request_only() -> None:
    import tempfile
    from pathlib import Path

    db_path = Path(tempfile.mktemp(suffix=".sqlite"))
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        owner = User(telegram_user_id=927, role="SUPER_ADMIN")
        session.add(owner)
        await session.flush()
        owner_id = owner.id
        await session.commit()

    async def invoke(subject: str) -> object:
        async with sessions() as session:
            try:
                return await provision_test_identity(
                    session, actor_user_id=owner_id, provider="telegram", subject=subject,
                    username="conflict", role="STUDENT", tenant_id=None,
                    audit_reason="conflict qualification", idempotency_key="conflict-key",
                )
            except ProvisioningDenied as exc:
                return exc

    results = await asyncio.gather(invoke("928"), invoke("929"))
    assert sum(hasattr(result, "status") for result in results) == 1
    assert sum(isinstance(result, ProvisioningDenied) for result in results) == 1
    await engine.dispose()
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_postgres_concurrent_same_key_has_created_and_replay() -> None:
    """Qualify the production transaction path against an ephemeral PostgreSQL DB."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL qualification")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.connect() as connection_a, engine.connect() as connection_b:
        backend_a = await connection_a.scalar(text("SELECT pg_backend_pid()"))
        backend_b = await connection_b.scalar(text("SELECT pg_backend_pid()"))
    assert backend_a != backend_b
    async with sessions() as session:
        suffix = uuid4().int % 1_000_000_000
        owner = User(telegram_user_id=992500 + suffix, role="SUPER_ADMIN")
        session.add(owner)
        await session.commit()
        owner_id = owner.id

    key = f"postgres-concurrency-qualification-{uuid4()}"

    async def invoke() -> object:
        async with sessions() as session:
            return await provision_test_identity(
                session,
                actor_user_id=owner_id,
                provider="telegram",
                subject=str(992501 + suffix),
                username=f"postgres-concurrency-{suffix}",
                role="STUDENT",
                tenant_id=None,
                audit_reason="postgres concurrency qualification",
                idempotency_key=key,
            )

    results = await asyncio.gather(invoke(), invoke())
    assert sorted(result.status for result in results) == ["CREATED", "REPLAY"]
    assert len({result.user_id for result in results}) == 1
    async with sessions() as session:
        records = (await session.scalars(
            select(ProvisioningIdempotencyKey).where(
                ProvisioningIdempotencyKey.idempotency_key == key
            )
        )).all()
        identities = (await session.scalars(
            select(User).where(User.telegram_user_id == 992501 + suffix)
        )).all()
    assert len(records) == 1
    assert len(identities) == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_end_to_end_audit_and_correlation_trace() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        owner = User(telegram_user_id=940, role="SUPER_ADMIN")
        session.add(owner)
        await session.flush()
        await session.commit()
        result = await provision_test_identity(
            session, actor_user_id=owner.id, provider="telegram", subject="941",
            username="trace", role="STUDENT", tenant_id=None,
            audit_reason="e2e qualification", idempotency_key="e2e-key",
            correlation_id="corr-e2e-941",
        )
        record = await session.scalar(select(ProvisioningIdempotencyKey).where(
            ProvisioningIdempotencyKey.idempotency_key == "e2e-key"
        ))
        audit = await session.scalar(select(AuditLog).where(AuditLog.id == result.audit_id))
        assert record is not None and record.correlation_id == "corr-e2e-941"
        assert audit is not None
        metadata = json.loads(audit.metadata_json)
        assert metadata["correlation_id"] == "corr-e2e-941"
        assert not any(key in metadata for key in ("token", "password", "secret"))
    await engine.dispose()
