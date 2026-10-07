"""Fresh, read-only principal authority facts for future control-plane policy.

This module deliberately does not authorize actions. Callers must supply only an
authenticated subject, a user lookup session, and a lifecycle reader that is
already allowed to invoke the qualified A11 resolver. It is not wired to routes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol, cast

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.security.canonical import canonical_role

CanonicalRole = Literal["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT"]
_CANONICAL_SUBJECT = re.compile(r"[1-9][0-9]*\Z")


class PrincipalAuthorityResolutionError(RuntimeError):
    """Base error: no authoritative snapshot is available."""


class InvalidPrincipalSubject(PrincipalAuthorityResolutionError):
    """The authenticated subject is not a canonical application user ID."""


class PrincipalNotFound(PrincipalAuthorityResolutionError):
    """No current user row exists for the authenticated subject."""


class PrincipalLookupUnavailable(PrincipalAuthorityResolutionError):
    """The current user could not be loaded from authoritative persistence."""


class StoredRoleNotCanonical(PrincipalAuthorityResolutionError):
    """The stored user role is outside the canonical four-role allowlist."""


class LifecycleStateUnavailable(PrincipalAuthorityResolutionError):
    """The qualified A11 lifecycle authority could not return a valid state."""


class LifecycleStateReader(Protocol):
    async def resolve_state(self, principal_ref: str, /) -> str:
        """Read and verify lifecycle state for one canonical principal reference."""


class PrincipalLifecycleState(StrEnum):
    UNRECONCILED = "UNRECONCILED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


@dataclass(frozen=True, slots=True)
class PrincipalAuthoritySnapshot:
    """Minimum fresh principal facts; this value contains no authorization grant."""

    principal_id: int
    role: CanonicalRole
    lifecycle_state: PrincipalLifecycleState


class A11LifecycleStateReader:
    """Read state through A11's integrity-checking, read-only SQL function.

    The supplied session must belong to a future identity explicitly authorized
    to execute ``maos_lifecycle.resolve_state``. A11 intentionally denies this
    function to ``app_runtime``; this class creates no grants or role bindings.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_state(self, principal_ref: str, /) -> str:
        result = await self._session.scalar(
            text("SELECT maos_lifecycle.resolve_state(:principal_ref)"),
            {"principal_ref": principal_ref},
        )
        if not isinstance(result, str):
            raise LifecycleStateUnavailable("A11 lifecycle resolver returned no state")
        return result


async def resolve_principal_authority_snapshot(
    authenticated_subject: str,
    user_session: AsyncSession,
    lifecycle_reader: LifecycleStateReader,
) -> PrincipalAuthoritySnapshot:
    """Load the current role and lifecycle facts without trusting JWT role claims.

    ``authenticated_subject`` is only a lookup key. This function accepts no JWT
    role, tenant selector, or caller-provided target identity and performs no DML.
    """

    if not isinstance(authenticated_subject, str) or not _CANONICAL_SUBJECT.fullmatch(
        authenticated_subject
    ):
        raise InvalidPrincipalSubject("Authenticated subject must be a canonical user ID")

    try:
        user_id = int(authenticated_subject)
        row = (
            await user_session.execute(
                select(User.id, User.role).where(User.id == user_id)
            )
        ).one_or_none()
    except Exception as exc:
        raise PrincipalLookupUnavailable("Current principal lookup failed") from exc

    if row is None:
        raise PrincipalNotFound("Authenticated principal does not exist")

    principal_id, stored_role = row
    try:
        current_role = cast(CanonicalRole, canonical_role(stored_role))
    except HTTPException as exc:
        raise StoredRoleNotCanonical("Stored principal role is not canonical") from exc

    principal_ref = f"user:{principal_id}"
    try:
        raw_lifecycle_state = await lifecycle_reader.resolve_state(principal_ref)
        lifecycle_state = PrincipalLifecycleState(raw_lifecycle_state)
    except Exception as exc:
        raise LifecycleStateUnavailable("Current A11 lifecycle state is unavailable") from exc

    return PrincipalAuthoritySnapshot(
        principal_id=principal_id,
        role=current_role,
        lifecycle_state=lifecycle_state,
    )
