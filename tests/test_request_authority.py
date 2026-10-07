from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import FrozenInstanceError
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    SchoolAdminMembership,
    SchoolTenant,
    TeacherProfile,
    User,
    UserTenantMembership,
)
from app.security.authority_snapshot import (
    LifecycleStateUnavailable,
    PrincipalAuthoritySnapshot,
    PrincipalLifecycleState,
    PrincipalNotFound,
)
from app.security.request_authority import (
    RequestAuthorityContextV1,
    resolve_request_authority_context,
)
from app.security.tenant_authority_snapshot import (
    AmbiguousTenantAuthority,
    TenantAuthorityDenied,
    TenantAuthorityUnavailable,
)
from app.security.tokens import create_access_token, decode_access_token_claims

pytestmark = pytest.mark.asyncio


class StaticLifecycleReader:
    def __init__(self, state: str = "ACTIVE", error: Exception | None = None) -> None:
        self.state = state
        self.error = error
        self.principal_refs: list[str] = []

    async def resolve_state(self, principal_ref: str, /) -> str:
        self.principal_refs.append(principal_ref)
        if self.error is not None:
            raise self.error
        return self.state


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        db.add_all(
            [
                User(id=1, telegram_user_id=10_001, role="TEACHER"),
                User(id=2, telegram_user_id=10_002, role="SUPER_ADMIN"),
                SchoolTenant(tenant_id="tenant-a", school_name="A"),
                SchoolTenant(tenant_id="tenant-b", school_name="B"),
            ]
        )
        await db.flush()
        yield db
    await engine.dispose()


async def test_composes_distinct_immutable_snapshots(session: AsyncSession) -> None:
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"))
    await session.flush()

    context = await resolve_request_authority_context("1", session, StaticLifecycleReader())

    assert isinstance(context, RequestAuthorityContextV1)
    assert context.principal == PrincipalAuthoritySnapshot(
        principal_id=1,
        role="TEACHER",  # type: ignore[arg-type]
        lifecycle_state=PrincipalLifecycleState.ACTIVE,
    )
    assert context.tenant.tenant_id == "tenant-a"
    assert context.tenant.principal_ref == "user:1"
    assert not hasattr(context.principal, "tenant_id")
    assert not hasattr(context.tenant, "role")
    with pytest.raises(FrozenInstanceError):
        context.tenant = context.tenant  # type: ignore[misc]


async def test_stale_jwt_role_does_not_change_composed_current_principal(
    session: AsyncSession,
) -> None:
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"))
    await session.flush()
    secret = "unit-test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("1", secret, role="SUPER_ADMIN")
    claims = decode_access_token_claims(token, secret)

    context = await resolve_request_authority_context(
        claims["sub"], session, StaticLifecycleReader()
    )

    assert claims["role"] == "SUPER_ADMIN"
    assert context.principal.role == "TEACHER"
    assert context.tenant.tenant_id == "tenant-a"


async def test_principal_resolution_precedes_tenant_resolution(monkeypatch, session) -> None:
    order: list[str] = []
    principal = PrincipalAuthoritySnapshot(
        principal_id=1,
        role="TEACHER",  # type: ignore[arg-type]
        lifecycle_state=PrincipalLifecycleState.ACTIVE,
    )

    async def resolve_principal(subject: str, db: AsyncSession, reader: Any):
        assert subject == "1"
        assert db is session
        order.append("principal")
        return principal

    async def resolve_tenant(snapshot: PrincipalAuthoritySnapshot, db: AsyncSession):
        assert snapshot is principal
        assert db is session
        order.append("tenant")
        from app.security.tenant_authority_snapshot import (
            TenantAuthoritySnapshotV1,
            TenantResolutionStatus,
        )

        return TenantAuthoritySnapshotV1(
            principal_ref="user:1",
            tenant_id="tenant-a",
            resolution_status=TenantResolutionStatus.RESOLVED_UNIQUE,
        )

    monkeypatch.setattr(
        "app.security.request_authority.resolve_principal_authority_snapshot", resolve_principal
    )
    monkeypatch.setattr(
        "app.security.request_authority.resolve_tenant_authority_snapshot", resolve_tenant
    )

    await resolve_request_authority_context("1", session, StaticLifecycleReader())

    assert order == ["principal", "tenant"]


@pytest.mark.parametrize(
    "error", [PrincipalNotFound("missing"), LifecycleStateUnavailable("unavailable")]
)
async def test_principal_failure_stops_before_tenant_resolution(
    monkeypatch, session: AsyncSession, error: Exception
) -> None:
    tenant_called = False

    async def fail_principal(*args: Any, **kwargs: Any):
        raise error

    async def tenant_must_not_run(*args: Any, **kwargs: Any):
        nonlocal tenant_called
        tenant_called = True
        raise AssertionError("tenant resolver must not run after principal failure")

    monkeypatch.setattr(
        "app.security.request_authority.resolve_principal_authority_snapshot", fail_principal
    )
    monkeypatch.setattr(
        "app.security.request_authority.resolve_tenant_authority_snapshot", tenant_must_not_run
    )

    with pytest.raises(type(error)):
        await resolve_request_authority_context("1", session, StaticLifecycleReader())

    assert tenant_called is False


@pytest.mark.parametrize(
    ("memberships", "error_type"),
    [
        ([], TenantAuthorityDenied),
        ([("tenant-a", "ACTIVE", None), ("tenant-b", "ACTIVE", None)], AmbiguousTenantAuthority),
        ([ ("tenant-a", "REVOKED", None) ], TenantAuthorityDenied),
        ([ ("tenant-a", "SUSPENDED", None) ], TenantAuthorityDenied),
    ],
)
async def test_membership_denials_propagate_through_composed_boundary(
    session: AsyncSession, memberships, error_type
) -> None:
    session.add_all(
        [
            UserTenantMembership(
                user_id=1, tenant_id=tenant_id, status=status, revoked_at=revoked_at
            )
            for tenant_id, status, revoked_at in memberships
        ]
    )
    await session.flush()

    with pytest.raises(error_type):
        await resolve_request_authority_context("1", session, StaticLifecycleReader())


async def test_revocation_timestamp_fails_composed_resolution(session: AsyncSession) -> None:
    from datetime import UTC, datetime

    session.add(
        UserTenantMembership(
            user_id=1,
            tenant_id="tenant-a",
            status="ACTIVE",
            revoked_at=datetime.now(UTC),
        )
    )
    await session.flush()

    with pytest.raises(TenantAuthorityDenied):
        await resolve_request_authority_context("1", session, StaticLifecycleReader())


async def test_super_admin_without_membership_gets_no_composed_tenant(session: AsyncSession) -> None:
    with pytest.raises(TenantAuthorityDenied):
        await resolve_request_authority_context("2", session, StaticLifecycleReader())


async def test_legacy_memberships_alone_do_not_compose_authority(session: AsyncSession) -> None:
    session.add_all(
        [
            TeacherProfile(teacher_id=1, tenant_id="tenant-a"),
            SchoolAdminMembership(user_id=1, tenant_id="tenant-b", status="ACTIVE"),
        ]
    )
    await session.flush()

    with pytest.raises(TenantAuthorityDenied):
        await resolve_request_authority_context("1", session, StaticLifecycleReader())


async def test_composition_api_rejects_selector_jwt_tenant_and_guc_inputs(
    session: AsyncSession,
) -> None:
    session.add(UserTenantMembership(user_id=1, tenant_id="tenant-a", status="ACTIVE"))
    await session.flush()

    for extra in (
        {"tenant_id": "tenant-b"},
        {"jwt_tenant": "tenant-b"},
        {"guc_tenant": "tenant-b"},
        {"role": "SUPER_ADMIN"},
    ):
        with pytest.raises(TypeError):
            await resolve_request_authority_context(  # type: ignore[call-arg]
                "1", session, StaticLifecycleReader(), **extra
            )


@pytest.mark.parametrize("error", [TenantAuthorityDenied("denied"), TenantAuthorityUnavailable("db")])
async def test_tenant_failures_propagate_without_returning_partial_context(
    monkeypatch, session: AsyncSession, error: Exception
) -> None:
    principal = PrincipalAuthoritySnapshot(
        principal_id=1,
        role="TEACHER",  # type: ignore[arg-type]
        lifecycle_state=PrincipalLifecycleState.ACTIVE,
    )

    async def resolve_principal(*args: Any, **kwargs: Any):
        return principal

    async def fail_tenant(*args: Any, **kwargs: Any):
        raise error

    monkeypatch.setattr(
        "app.security.request_authority.resolve_principal_authority_snapshot", resolve_principal
    )
    monkeypatch.setattr(
        "app.security.request_authority.resolve_tenant_authority_snapshot", fail_tenant
    )

    with pytest.raises(type(error)):
        await resolve_request_authority_context("1", session, StaticLifecycleReader())
