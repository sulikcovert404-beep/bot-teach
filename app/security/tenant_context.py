"""Authenticated request tenant resolution and transaction-local context."""

from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.base import set_tenant_context
from app.security.dependencies import require_roles
from app.security.tenant_resolver import TenantResolutionError, resolve_tenant


@dataclass(frozen=True)
class TenantContext:
    user_id: int
    tenant_id: str


async def establish_tenant_context(session: AsyncSession, *, user_id: int) -> TenantContext:
    """Resolve authenticated identity and set RLS context on the same session."""
    try:
        if not session.in_transaction():
            await session.begin()
        tenant_id = await resolve_tenant(session, user_id=user_id)
        await set_tenant_context(session, tenant_id)
    except (TenantResolutionError, ValueError) as exc:
        await session.rollback()
        raise HTTPException(status_code=403, detail="Tenant scope denied") from exc
    return TenantContext(user_id=user_id, tenant_id=tenant_id)


@lru_cache(maxsize=8)
def tenant_context_for(*allowed_roles: str):
    """Return a cached FastAPI dependency for the requested authenticated roles."""
    authenticate = require_roles(*allowed_roles)

    async def dependency(
        subject: str = Depends(authenticate),
        session: AsyncSession = Depends(get_session),  # noqa: B008
    ) -> TenantContext:
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid user identity") from exc
        return await establish_tenant_context(session, user_id=user_id)

    return dependency
