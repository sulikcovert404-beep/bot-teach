from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import User
from app.security.authority_snapshot import (
    A11LifecycleStateReader,
    InvalidPrincipalSubject,
    LifecycleStateUnavailable,
    PrincipalAuthoritySnapshot,
    PrincipalLifecycleState,
    PrincipalNotFound,
    StoredRoleNotCanonical,
    resolve_principal_authority_snapshot,
)
from app.security.tokens import create_access_token, decode_access_token_claims

pytestmark = pytest.mark.asyncio


class StaticLifecycleReader:
    def __init__(self, state: str = "UNRECONCILED", error: Exception | None = None) -> None:
        self.state = state
        self.error = error
        self.principal_refs: list[str] = []

    async def resolve_state(self, principal_ref: str, /) -> str:
        self.principal_refs.append(principal_ref)
        if self.error is not None:
            raise self.error
        return self.state


@pytest_asyncio.fixture
async def user_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _add_user(session: AsyncSession, user_id: int, role: str) -> User:
    user = User(id=user_id, telegram_user_id=user_id + 10_000, role=role)
    session.add(user)
    await session.commit()
    return user


@pytest.mark.parametrize("subject", ["", "0", "01", "+1", "-1", " 1", "one"])
async def test_noncanonical_subject_fails_before_database_or_lifecycle_lookup(
    user_session: AsyncSession, subject: str
) -> None:
    reader = StaticLifecycleReader()

    with pytest.raises(InvalidPrincipalSubject):
        await resolve_principal_authority_snapshot(subject, user_session, reader)

    assert reader.principal_refs == []


async def test_missing_principal_fails_closed_without_lifecycle_lookup(
    user_session: AsyncSession,
) -> None:
    reader = StaticLifecycleReader()

    with pytest.raises(PrincipalNotFound):
        await resolve_principal_authority_snapshot("404", user_session, reader)

    assert reader.principal_refs == []


@pytest.mark.parametrize("role", ["ADMIN", "ROOT", "TEACHER_ADMIN", "super_admin", "UNKNOWN"])
async def test_legacy_or_unknown_stored_role_fails_closed(
    user_session: AsyncSession, role: str
) -> None:
    await _add_user(user_session, 23, role)
    reader = StaticLifecycleReader()

    with pytest.raises(StoredRoleNotCanonical):
        await resolve_principal_authority_snapshot("23", user_session, reader)

    assert reader.principal_refs == []


@pytest.mark.parametrize("role", ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT"])
async def test_snapshot_uses_current_canonical_database_role(
    user_session: AsyncSession, role: str
) -> None:
    await _add_user(user_session, 23, role)
    reader = StaticLifecycleReader("ACTIVE")

    snapshot = await resolve_principal_authority_snapshot("23", user_session, reader)

    assert snapshot == PrincipalAuthoritySnapshot(
        principal_id=23,
        role=role,  # type: ignore[arg-type]
        lifecycle_state=PrincipalLifecycleState.ACTIVE,
    )
    assert reader.principal_refs == ["user:23"]


async def test_elevated_jwt_role_does_not_override_lower_current_database_role(
    user_session: AsyncSession,
) -> None:
    await _add_user(user_session, 23, "STUDENT")
    token = create_access_token("23", "unit-test-secret-key-that-is-at-least-32-bytes", role="SUPER_ADMIN")
    claims = decode_access_token_claims(token, "unit-test-secret-key-that-is-at-least-32-bytes")
    reader = StaticLifecycleReader("ACTIVE")

    snapshot = await resolve_principal_authority_snapshot(claims["sub"], user_session, reader)

    assert claims["role"] == "SUPER_ADMIN"
    assert snapshot.role == "STUDENT"


async def test_lower_jwt_role_does_not_hide_current_database_role(
    user_session: AsyncSession,
) -> None:
    await _add_user(user_session, 23, "SUPER_ADMIN")
    token = create_access_token("23", "unit-test-secret-key-that-is-at-least-32-bytes", role="STUDENT")
    claims = decode_access_token_claims(token, "unit-test-secret-key-that-is-at-least-32-bytes")
    reader = StaticLifecycleReader("ACTIVE")

    snapshot = await resolve_principal_authority_snapshot(claims["sub"], user_session, reader)

    assert claims["role"] == "STUDENT"
    assert snapshot.role == "SUPER_ADMIN"


async def test_role_change_is_refetched_from_database_on_each_call(
    user_session: AsyncSession,
) -> None:
    user = await _add_user(user_session, 23, "STUDENT")
    reader = StaticLifecycleReader("ACTIVE")

    first = await resolve_principal_authority_snapshot("23", user_session, reader)
    user.role = "TEACHER"
    await user_session.commit()
    second = await resolve_principal_authority_snapshot("23", user_session, reader)

    assert first.role == "STUDENT"
    assert second.role == "TEACHER"


@pytest.mark.parametrize(
    "state",
    ["UNRECONCILED", "ACTIVE", "SUSPENDED", "DISABLED"],
)
async def test_snapshot_preserves_each_a11_lifecycle_state(
    user_session: AsyncSession, state: str
) -> None:
    await _add_user(user_session, 23, "STUDENT")
    reader = StaticLifecycleReader(state)

    snapshot = await resolve_principal_authority_snapshot("23", user_session, reader)

    assert snapshot.lifecycle_state is PrincipalLifecycleState(state)
    assert not hasattr(snapshot, "is_active")
    assert not hasattr(snapshot, "tenant_id")


async def test_lifecycle_resolver_failure_and_unknown_state_fail_closed(
    user_session: AsyncSession,
) -> None:
    await _add_user(user_session, 23, "STUDENT")

    for reader in (
        StaticLifecycleReader(error=RuntimeError("database detail must not escape")),
        StaticLifecycleReader("ACTIVE "),
    ):
        with pytest.raises(LifecycleStateUnavailable) as raised:
            await resolve_principal_authority_snapshot("23", user_session, reader)
        assert str(raised.value) == "Current A11 lifecycle state is unavailable"


async def test_a11_reader_uses_only_the_qualified_read_function() -> None:
    class SessionProbe:
        def __init__(self) -> None:
            self.statement = ""
            self.parameters: dict[str, str] = {}

        async def scalar(self, statement: Any, parameters: dict[str, str]) -> str:
            self.statement = str(statement)
            self.parameters = parameters
            return "SUSPENDED"

    probe = SessionProbe()
    state = await A11LifecycleStateReader(probe).resolve_state("user:23")  # type: ignore[arg-type]

    assert state == "SUSPENDED"
    assert "SELECT maos_lifecycle.resolve_state(:principal_ref)" in probe.statement
    assert "append_event" not in probe.statement
    assert probe.parameters == {"principal_ref": "user:23"}
