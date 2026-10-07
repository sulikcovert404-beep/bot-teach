"""Typed, read-only tenant authority derived from canonical membership."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.security.authority_snapshot import (
    PrincipalAuthoritySnapshot,
    PrincipalLifecycleState,
)
from app.security.tenant_resolver import (
    AmbiguousTenantError,
    TenantResolutionError,
    resolve_tenant,
)


class TenantAuthorityResolutionError(PermissionError):
    """Base error raised when current tenant authority cannot be established."""


class InvalidPrincipalAuthority(TenantAuthorityResolutionError):
    """The supplied principal snapshot is malformed or not canonical."""


class TenantAuthorityDenied(TenantAuthorityResolutionError):
    """No unique active, non-revoked canonical tenant membership exists."""


class AmbiguousTenantAuthority(TenantAuthorityDenied):
    """More than one eligible tenant membership exists in the local adapter."""


class TenantAuthorityUnavailable(TenantAuthorityResolutionError):
    """The canonical tenant authority source could not be read safely."""


class TenantResolutionStatus(StrEnum):
    RESOLVED_UNIQUE = "RESOLVED_UNIQUE"


@dataclass(frozen=True, slots=True)
class TenantAuthoritySnapshotV1:
    """Minimal tenant authority facts; this snapshot is not an authorization grant."""

    principal_ref: str
    tenant_id: str
    resolution_status: TenantResolutionStatus


_CANONICAL_ROLES = frozenset({"SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT"})


def _validate_principal(principal: PrincipalAuthoritySnapshot) -> None:
    if not isinstance(principal, PrincipalAuthoritySnapshot):
        raise InvalidPrincipalAuthority("A verified principal authority snapshot is required")
    if type(principal.principal_id) is not int or principal.principal_id <= 0:
        raise InvalidPrincipalAuthority("Principal snapshot has an invalid canonical ID")
    if principal.role not in _CANONICAL_ROLES:
        raise InvalidPrincipalAuthority("Principal snapshot has a noncanonical role")
    if not isinstance(principal.lifecycle_state, PrincipalLifecycleState):
        raise InvalidPrincipalAuthority("Principal snapshot has an invalid lifecycle state")


async def resolve_tenant_authority_snapshot(
    principal: PrincipalAuthoritySnapshot,
    session: AsyncSession,
) -> TenantAuthoritySnapshotV1:
    """Resolve tenant authority only from a fresh principal snapshot and canonical resolver.

    This function deliberately has no tenant-selector, JWT, legacy-membership, or
    GUC input. Lifecycle state is validated as part of the principal snapshot but
    is not converted into tenant policy here.
    """

    _validate_principal(principal)
    principal_ref = f"user:{principal.principal_id}"
    try:
        tenant_id = await resolve_tenant(session, user_id=principal.principal_id)
    except AmbiguousTenantError as exc:
        raise AmbiguousTenantAuthority("Canonical tenant membership is ambiguous") from exc
    except TenantResolutionError as exc:
        raise TenantAuthorityDenied("No unique active tenant membership exists") from exc
    except Exception as exc:
        raise TenantAuthorityUnavailable("Canonical tenant resolver is unavailable") from exc

    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise TenantAuthorityUnavailable("Canonical tenant resolver returned an invalid result")

    return TenantAuthoritySnapshotV1(
        principal_ref=principal_ref,
        tenant_id=tenant_id,
        resolution_status=TenantResolutionStatus.RESOLVED_UNIQUE,
    )
