"""Compose fresh principal and canonical tenant authority facts for a request.

This is an unwired, read-only seam. It neither authorizes an operation nor
establishes transaction-local tenant context.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.security.authority_snapshot import (
    LifecycleStateReader,
    PrincipalAuthoritySnapshot,
    resolve_principal_authority_snapshot,
)
from app.security.tenant_authority_snapshot import (
    TenantAuthoritySnapshotV1,
    resolve_tenant_authority_snapshot,
)


@dataclass(frozen=True, slots=True)
class RequestAuthorityContextV1:
    """Keep fresh principal and tenant facts distinct and immutable."""

    principal: PrincipalAuthoritySnapshot
    tenant: TenantAuthoritySnapshotV1


async def resolve_request_authority_context(
    authenticated_subject: str,
    user_session: AsyncSession,
    lifecycle_reader: LifecycleStateReader,
) -> RequestAuthorityContextV1:
    """Resolve principal first, then its unique canonical tenant membership.

    The authenticated subject is only the lookup key accepted by the qualified
    principal resolver. All denials and unavailable states propagate fail-closed;
    no tenant selector, token role, legacy mapping, or GUC is consulted here.
    """

    principal = await resolve_principal_authority_snapshot(
        authenticated_subject,
        user_session,
        lifecycle_reader,
    )
    tenant = await resolve_tenant_authority_snapshot(principal, user_session)
    return RequestAuthorityContextV1(principal=principal, tenant=tenant)
