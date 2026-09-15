"""Server-side identity-to-tenant resolution boundary.

The production database function remains the authoritative boundary once
 migrated. This ORM adapter mirrors its fail-closed semantics for disposable
 application qualification and never accepts a client-supplied tenant.
"""
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserTenantMembership


class TenantResolutionError(PermissionError):
    """Base class for fail-closed tenant resolution failures."""


class AmbiguousTenantError(TenantResolutionError):
    pass


async def resolve_tenant(session: AsyncSession, *, user_id: int) -> str:
    # PostgreSQL uses the approved SECURITY DEFINER boundary, so the runtime
    # role never receives direct membership-table read access. SQLite remains
    # available for fast unit tests through the ORM fallback.
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        tenant = await session.scalar(text("SELECT resolve_tenant(:user_id)"), {"user_id": user_id})
        if tenant is None:
            raise TenantResolutionError("no unique active tenant membership")
        return str(tenant)
    rows = (
        await session.scalars(
            select(UserTenantMembership.tenant_id)
            .where(
                UserTenantMembership.user_id == user_id,
                UserTenantMembership.status == "ACTIVE",
                UserTenantMembership.revoked_at.is_(None),
            )
            .order_by(UserTenantMembership.tenant_id)
            .limit(2)
        )
    ).all()
    if not rows:
        raise TenantResolutionError("no active tenant membership")
    if len(rows) > 1:
        raise AmbiguousTenantError("ambiguous active tenant membership")
    return rows[0]
