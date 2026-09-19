import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import AuditLog, SchoolTenant, StudentProfile, User
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
