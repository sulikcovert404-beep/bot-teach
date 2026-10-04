from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from functools import lru_cache
from time import monotonic

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.logging import writer_metrics


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


_WRITER_DML = re.compile(
    r"^\s*(?:(?:--[^\n]*\n\s*)|(?:/\*.*?\*/\s*))*"
    r"(?:INSERT|UPDATE|DELETE|MERGE)\b|"
    r"^\s*WITH\b.*\b(?:INSERT|UPDATE|DELETE|MERGE)\b",
    re.IGNORECASE | re.DOTALL,
)


def _install_writer_admission(engine, generation: str, instance_id: str) -> None:
    """Fence SQLAlchemy writes at one shared engine boundary.

    Admission is rechecked before every DML statement so a savepoint rollback
    cannot accidentally release the database lock and leave later writes in
    the same root transaction unchecked.
    """

    def before_execute(connection, clauseelement, multiparams, params, execution_options):
        is_dml = any(
            bool(getattr(clauseelement, attribute, False))
            for attribute in ("is_insert", "is_update", "is_delete")
        )
        statement = getattr(clauseelement, "text", None)
        if not is_dml and isinstance(statement, str):
            is_dml = bool(_WRITER_DML.search(statement))
        if not is_dml:
            return
        connection.execute(
            text("SELECT public.gate738k_admit_writer()"),
        )
        info = connection.info
        if "gate738k_writer_started" not in info:
            info["gate738k_writer_started"] = monotonic()
            info["gate738k_writer_generation"] = generation
            info["gate738k_writer_instance"] = instance_id
            writer_metrics.enter(generation, instance_id)

    def finish_connection_info(info) -> None:
        started = info.pop("gate738k_writer_started", None)
        release = info.pop("gate738k_writer_generation", None)
        instance = info.pop("gate738k_writer_instance", None)
        if started is not None and release is not None and instance is not None:
            writer_metrics.leave(release, instance, monotonic() - started)

    def finish_connection_record(_dbapi_connection, connection_record, *_event_args) -> None:
        finish_connection_info(connection_record.info)

    event.listen(engine, "before_execute", before_execute)
    # Checkin occurs after transaction completion. Pool invalidation handles
    # server crashes; retaining a local positive gauge until then is conservative.
    event.listen(engine.pool, "checkin", finish_connection_record)
    event.listen(engine.pool, "invalidate", finish_connection_record)
    event.listen(engine.pool, "soft_invalidate", finish_connection_record)


@lru_cache(maxsize=16)
def build_session_factory(
    database_url: str,
    writer_admission_enabled: bool = False,
    writer_generation: str = "",
    writer_instance_id: str = "",
    writer_database_role: str = "",
) -> async_sessionmaker[AsyncSession]:
    if not database_url:
        raise ValueError("DATABASE_URL is required to create a database session")
    if writer_admission_enabled:
        if not database_url.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise ValueError("writer admission requires PostgreSQL")
        if not writer_generation or not writer_instance_id:
            raise ValueError("writer admission requires generation and instance identifiers")
        writer_database_role = writer_database_role or (make_url(database_url).username or "")
        if not writer_database_role:
            raise ValueError("writer admission requires a database login role")
        if writer_generation == "legacy" and writer_database_role != "app_runtime":
            raise ValueError("legacy writer admission requires app_runtime")
        if writer_generation != "legacy" and writer_database_role == "app_runtime":
            raise ValueError("candidate writer admission requires a distinct database login role")
        if make_url(database_url).username != writer_database_role:
            raise ValueError("writer database URL does not match its registered PostgreSQL role")
    connect_args = {}
    if writer_admission_enabled:
        # application_name is operational metadata only. Database admission
        # identity comes from PostgreSQL session_user, never this caller tag.
        connect_args = {
            "server_settings": {
                "application_name": f"aitw:{writer_generation}:{writer_instance_id}"
            }
        }
    engine = create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    if writer_admission_enabled:
        _install_writer_admission(engine.sync_engine, writer_generation, writer_instance_id)
    return async_sessionmaker(engine, expire_on_commit=False)


async def dispose_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    bind = factory.kw.get("bind")
    if bind is not None and hasattr(bind, "dispose"):
        await bind.dispose()


async def session_dependency(factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with factory() as session:
        yield session
