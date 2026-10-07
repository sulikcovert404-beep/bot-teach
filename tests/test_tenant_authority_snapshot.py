from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    SchoolAdminMembership,
    SchoolTenant,
    TeacherProfile,
    User,
    UserTenantMembership,
)
from app.security.authority_snapshot import (
    PrincipalAuthoritySnapshot,
    PrincipalLifecycleState,
)
from app.security.tenant_authority_snapshot import (
    AmbiguousTenantAuthority,
    InvalidPrincipalAuthority,
    TenantAuthorityDenied,
    TenantAuthoritySnapshotV1,
    TenantAuthorityUnavailable,
    TenantResolutionStatus,
    resolve_tenant_authority_snapshot,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        db.add_all(
            [
                User(id=1, role="TEACHER"),
                User(id=2, role="SUPER_ADMIN"),
                SchoolTenant(tenant_id="tenant-a", school_name="A"),
                SchoolTenant(tenant_id="tenant-b", school_name="B"),
            ]
        )
        await db.flush()
        yield db
    await engine.dispose()


def principal(
    principal_id: int = 1,
    *,
    role: str = "TEACHER",
    lifecycle: PrincipalLifecycleState = PrincipalLifecycleState.ACTIVE,
) -> PrincipalAuthoritySnapshot:
    return PrincipalAuthoritySnapshot(
        principal_id=principal_id,
        role=role,  # type: ignore[arg-type]
        lifecycle_state=lifecycle,
    )


@pytest.mark.asyncio
async def test_single_active_membership_returns_minimal_immutable_snapshot(session):
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"))
    await session.flush()

    result = await resolve_tenant_authority_snapshot(principal(), session)

    assert result == TenantAuthoritySnapshotV1(
        principal_ref="user:1",
        tenant_id="tenant-a",
        resolution_status=TenantResolutionStatus.RESOLVED_UNIQUE,
    )
    assert not hasattr(result, "role")
    assert not hasattr(result, "lifecycle_state")
    with pytest.raises(AttributeError):
        result.tenant_id = "tenant-b"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_zero_membership_fails_closed(session):
    with pytest.raises(TenantAuthorityDenied):
        await resolve_tenant_authority_snapshot(principal(), session)


@pytest.mark.asyncio
async def test_multiple_active_memberships_fail_closed_as_ambiguous(session):
    session.add_all(
        [
            UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"),
            UserTenantMembership(user_id=1, tenant_id="tenant-b", status="ACTIVE"),
        ]
    )
    await session.flush()

    with pytest.raises(AmbiguousTenantAuthority):
        await resolve_tenant_authority_snapshot(principal(), session)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "membership_values",
    [
        {"status": "REVOKED"},
        {"status": "SUSPENDED"},
        {"status": "ACTIVE", "revoked_at": datetime.now(UTC)},
    ],
)
async def test_revoked_or_inactive_membership_fails_closed(session, membership_values):
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", **membership_values))
    await session.flush()

    with pytest.raises(TenantAuthorityDenied):
        await resolve_tenant_authority_snapshot(principal(), session)


@pytest.mark.asyncio
async def test_legacy_memberships_alone_cannot_establish_authority(session):
    session.add_all(
        [
            TeacherProfile(teacher_id=1, tenant_id="tenant-a"),
            SchoolAdminMembership(user_id=1, tenant_id="tenant-b", status="ACTIVE"),
        ]
    )
    await session.flush()

    with pytest.raises(TenantAuthorityDenied):
        await resolve_tenant_authority_snapshot(principal(), session)


@pytest.mark.asyncio
async def test_super_admin_without_canonical_membership_gets_no_synthetic_scope(session):
    with pytest.raises(TenantAuthorityDenied):
        await resolve_tenant_authority_snapshot(principal(2, role="SUPER_ADMIN"), session)


@pytest.mark.asyncio
async def test_disabled_lifecycle_is_preserved_as_separate_dimension(session):
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"))
    await session.flush()

    result = await resolve_tenant_authority_snapshot(
        principal(lifecycle=PrincipalLifecycleState.DISABLED), session
    )

    assert result.tenant_id == "tenant-a"
    assert not hasattr(result, "lifecycle_state")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_principal",
    [
        None,
        "1",
        principal(0),
        principal(-1),
        principal(role="ADMIN"),
        PrincipalAuthoritySnapshot(
            principal_id=1,
            role="TEACHER",  # type: ignore[arg-type]
            lifecycle_state="ACTIVE",  # type: ignore[arg-type]
        ),
    ],
)
async def test_malformed_principal_fails_before_membership_lookup(session, bad_principal):
    with pytest.raises(InvalidPrincipalAuthority):
        await resolve_tenant_authority_snapshot(bad_principal, session)


@pytest.mark.asyncio
async def test_database_failure_fails_closed(monkeypatch, session):
    async def fail_resolver(_session, *, user_id: int) -> str:
        assert user_id == 1
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.security.tenant_authority_snapshot.resolve_tenant", fail_resolver)
    with pytest.raises(TenantAuthorityUnavailable):
        await resolve_tenant_authority_snapshot(principal(), session)


@pytest.mark.asyncio
async def test_selector_jwt_and_guc_values_are_not_inputs(session):
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"))
    await session.flush()

    result = await resolve_tenant_authority_snapshot(principal(), session)

    assert result.tenant_id == "tenant-a"
    with pytest.raises(TypeError):
        await resolve_tenant_authority_snapshot(  # type: ignore[call-arg]
            principal(),
            session,
            tenant_id="tenant-b",
        )
    with pytest.raises(TypeError):
        await resolve_tenant_authority_snapshot(  # type: ignore[call-arg]
            principal(),
            session,
            jwt_tenant="tenant-b",
        )
    with pytest.raises(TypeError):
        await resolve_tenant_authority_snapshot(  # type: ignore[call-arg]
            principal(),
            session,
            guc_tenant="tenant-b",
        )
