"""SQLAlchemy persistence runtime for the curriculum pipeline contracts."""
from __future__ import annotations

import json
import logging
from types import TracebackType
from typing import Any, Self

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    AuditLog,
    ContentVersion,
    IngestionIdempotencyKey,
    PublicationPointer,
    TransactionalOutboxEvent,
)

from .curriculum_pipeline_adapters import (
    AuditRepository,
    ContentVersionRepository,
    IdempotencyRepository,
    OutboxRepository,
    PublicationPointerRepository,
    UnitOfWork,
)
from .curriculum_pipeline_api import (
    CASConflictError,
    IdempotencyConflictError,
    IdempotencyRecordMissingError,
    SessionNotInitializedError,
)

logger = logging.getLogger(__name__)


class SQLAlchemyContentVersions(ContentVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    async def get_for_update(self, content_version_id: int) -> ContentVersion | None:
        statement = (
            select(ContentVersion)
            .where(ContentVersion.id == content_version_id)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
    async def save(self, version: ContentVersion, *, expected_version: int | None = None) -> None:
        self.session.add(version)


class SQLAlchemyPublicationPointers(PublicationPointerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def switch(
        self,
        source_document_id: int,
        content_version_id: int,
        *,
        expected_version: int | None = None,
    ) -> PublicationPointer:
        statement = (
            select(PublicationPointer)
            .where(PublicationPointer.source_document_id == source_document_id)
            .with_for_update()
        )
        current = (await self.session.execute(statement)).scalar_one_or_none()
        if current is None:
            if expected_version not in (None, 0):
                raise CASConflictError("publication pointer does not exist")
            current = PublicationPointer(
                source_document_id=source_document_id,
                content_version_id=content_version_id,
                version=1,
            )
            self.session.add(current)
            return current
        if expected_version is not None and current.version != expected_version:
            raise CASConflictError(
                f"pointer version conflict: expected {expected_version}, "
                f"current {current.version}"
            )
        current.content_version_id = content_version_id
        current.version += 1
        return current


class SQLAlchemyOutbox(OutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        event_id: str,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> None:
        self.session.add(
            TransactionalOutboxEvent(
                event_id=event_id,
                event_type=event_type,
                aggregate_type="curriculum",
                aggregate_id=aggregate_id,
                payload_json=json.dumps(
                    payload, ensure_ascii=False, sort_keys=True
                ),
            )
        )


class SQLAlchemyIdempotency(IdempotencyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    async def lock_or_get(self, key: str, request_hash: str) -> IngestionIdempotencyKey | None:
        statement = (
            select(IngestionIdempotencyKey)
            .where(IngestionIdempotencyKey.idempotency_key == key)
            .with_for_update()
        )
        row = (await self.session.execute(statement)).scalar_one_or_none()
        if row is not None and row.request_hash not in (None, request_hash):
            raise IdempotencyConflictError("idempotency key reused with a different request hash")
        if row is None:
            row = IngestionIdempotencyKey(
                idempotency_key=key,
                request_hash=request_hash,
                status="IN_PROGRESS",
            )
            self.session.add(row)
            await self.session.flush()
        return row
    async def complete(self, key: str, request_hash: str, response: dict[str, Any]) -> None:
        payload = json.dumps(response, ensure_ascii=False, sort_keys=True)
        statement = (
            update(IngestionIdempotencyKey)
            .where(
                IngestionIdempotencyKey.idempotency_key == key,
                IngestionIdempotencyKey.request_hash == request_hash,
                IngestionIdempotencyKey.status == "IN_PROGRESS",
            )
            .values(status="COMPLETED", response_json=payload)
            .returning(IngestionIdempotencyKey.id)
        )
        updated_id = (await self.session.execute(statement)).scalar_one_or_none()
        if updated_id is not None:
            return
        row = await self.session.scalar(
            select(IngestionIdempotencyKey).where(
                IngestionIdempotencyKey.idempotency_key == key
            )
        )
        if row is None:
            raise IdempotencyRecordMissingError("idempotency record does not exist")
        if row.request_hash != request_hash:
            raise IdempotencyConflictError("idempotency key reused with a different request hash")
        if row.status == "COMPLETED":
            return
        raise IdempotencyConflictError(
            f"idempotency record is not completable in status {row.status!r}"
        )


class SQLAlchemyAudit(AuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any],
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_json=json.dumps(
                    metadata, ensure_ascii=False, sort_keys=True
                ),
            )
        )


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self.factory()
        session = self.session
        self._content_versions = SQLAlchemyContentVersions(session)
        self._publication_pointers = SQLAlchemyPublicationPointers(session)
        self._outbox = SQLAlchemyOutbox(session)
        self._idempotency = SQLAlchemyIdempotency(session)
        self._audit = SQLAlchemyAudit(session)
        return self
    @property
    def content_versions(self) -> ContentVersionRepository: return self._content_versions
    @property
    def publication_pointers(
        self,
    ) -> PublicationPointerRepository: return self._publication_pointers
    @property
    def outbox(self) -> OutboxRepository: return self._outbox
    @property
    def idempotency(self) -> IdempotencyRepository: return self._idempotency
    @property
    def audit(self) -> AuditRepository: return self._audit

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        session = self.session
        if session is None:
            if exc_type is None:
                logger.warning("UnitOfWork exited without an active session")
            return None
        try:
            if exc_type is None:
                await session.commit()
            else:
                await session.rollback()
        except BaseException:
            if exc_type is None:
                raise
            logger.exception("UnitOfWork cleanup failed while preserving primary exception")
        finally:
            try:
                await session.close()
            except BaseException:
                if exc_type is None:
                    raise
                logger.exception("UnitOfWork close failed while preserving primary exception")
            finally:
                self.session = None
        return None

    async def commit(self) -> None:
        session = self.session
        if session is None:
            raise SessionNotInitializedError("cannot commit without an active session")
        await session.commit()

    async def rollback(self) -> None:
        session = self.session
        if session is None:
            raise SessionNotInitializedError("cannot rollback without an active session")
        await session.rollback()
