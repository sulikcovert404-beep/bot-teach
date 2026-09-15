import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import SchoolTenant, User, UserTenantMembership
from app.security.tenant_resolver import AmbiguousTenantError, TenantResolutionError, resolve_tenant


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        s.add_all([User(id=1), User(id=2), SchoolTenant(tenant_id="a", school_name="A"), SchoolTenant(tenant_id="b", school_name="B")])
        await s.flush()
        s.add(UserTenantMembership(user_id=1, tenant_id="a", status="ACTIVE"))
        await s.commit()
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_resolves_active_membership(session):
    assert await resolve_tenant(session, user_id=1) == "a"


@pytest.mark.asyncio
async def test_missing_and_revoked_fail_closed(session):
    with pytest.raises(TenantResolutionError):
        await resolve_tenant(session, user_id=2)
    session.add(UserTenantMembership(user_id=2, tenant_id="a", status="REVOKED"))
    await session.commit()
    with pytest.raises(TenantResolutionError):
        await resolve_tenant(session, user_id=2)


@pytest.mark.asyncio
async def test_ambiguous_membership_denied(session):
    session.add(UserTenantMembership(user_id=1, tenant_id="b", status="ACTIVE"))
    await session.commit()
    with pytest.raises(AmbiguousTenantError):
        await resolve_tenant(session, user_id=1)
