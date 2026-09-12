from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class InvalidTenantContext(ValueError):
    """Raised when a request attempts to establish an invalid tenant context."""


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> str:
    """Set a transaction-local tenant context before tenant-scoped queries.

    PostgreSQL's ``is_local=true`` ensures the setting is cleared on commit/rollback
    and cannot leak through a pooled connection. The value is bound as a parameter.
    """
    if not isinstance(tenant_id, str):
        raise InvalidTenantContext("tenant_id must be a string")
    raw = tenant_id
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", raw):
        raise InvalidTenantContext("tenant_id must be a valid opaque identifier")
    normalized = raw
    if not session.in_transaction():
        raise InvalidTenantContext("tenant context requires an active transaction")
    await session.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": normalized})
    return normalized


@lru_cache(maxsize=8)
def build_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    if not database_url:
        raise ValueError("DATABASE_URL is required to create a database session")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def dispose_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    bind = factory.kw.get("bind")
    if bind is not None and hasattr(bind, "dispose"):
        await bind.dispose()


async def session_dependency(factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with factory() as session:
        yield session
