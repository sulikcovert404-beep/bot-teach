"""SQLAlchemy persistence runtime for the curriculum pipeline contracts."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (AuditLog, ContentVersion, IngestionIdempotencyKey,
                           PublicationPointer, TransactionalOutboxEvent)
from .curriculum_pipeline_adapters import (AuditRepository, ContentVersionRepository,
    IdempotencyRepository, OutboxRepository, PublicationPointerRepository, UnitOfWork)
from .curriculum_pipeline_api import CASConflictError, IdempotencyConflictError


class SQLAlchemyContentVersions(ContentVersionRepository):
    def __init__(self, session: AsyncSession): self.session = session
    async def get_for_update(self, content_version_id: int) -> ContentVersion | None:
        return (await self.session.execute(select(ContentVersion).where(ContentVersion.id == content_version_id).with_for_update())).scalar_one_or_none()
    async def save(self, version: ContentVersion, *, expected_version: int | None = None) -> None:
        self.session.add(version)


class SQLAlchemyPublicationPointers(PublicationPointerRepository):
    def __init__(self, session: AsyncSession): self.session = session
    async def switch(self, source_document_id: int, content_version_id: int, *, expected_version: int | None = None) -> PublicationPointer:
        current = (await self.session.execute(select(PublicationPointer).where(PublicationPointer.source_document_id == source_document_id).with_for_update())).scalar_one_or_none()
        if current is None:
            if expected_version not in (None, 0): raise CASConflictError("publication pointer does not exist")
            current = PublicationPointer(source_document_id=source_document_id, content_version_id=content_version_id, version=1)
            self.session.add(current)
            return current
        if expected_version is not None and current.version != expected_version:
            raise CASConflictError(f"pointer version conflict: expected {expected_version}, current {current.version}")
        current.content_version_id = content_version_id
        current.version += 1
        return current


class SQLAlchemyOutbox(OutboxRepository):
    def __init__(self, session: AsyncSession): self.session = session
    async def append(self, event_id: str, event_type: str, aggregate_id: str, payload: dict[str, Any]) -> None:
        self.session.add(TransactionalOutboxEvent(event_id=event_id, event_type=event_type, aggregate_type="curriculum", aggregate_id=aggregate_id, payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True)))


class SQLAlchemyIdempotency(IdempotencyRepository):
    def __init__(self, session: AsyncSession): self.session = session
    async def lock_or_get(self, key: str, request_hash: str) -> IngestionIdempotencyKey | None:
        row = (await self.session.execute(select(IngestionIdempotencyKey).where(IngestionIdempotencyKey.idempotency_key == key).with_for_update())).scalar_one_or_none()
        if row is not None and row.request_hash not in (None, request_hash):
            raise IdempotencyConflictError("idempotency key reused with a different request hash")
        if row is None:
            row = IngestionIdempotencyKey(idempotency_key=key, request_hash=request_hash, status="IN_PROGRESS")
            self.session.add(row)
            await self.session.flush()
        return row
    async def complete(self, key: str, request_hash: str, response: dict[str, Any]) -> None:
        row = await self.lock_or_get(key, request_hash)
        row.status = "COMPLETED"; row.response_json = json.dumps(response, ensure_ascii=False, sort_keys=True)


class SQLAlchemyAudit(AuditRepository):
    def __init__(self, session: AsyncSession): self.session = session
    async def append(self, *, actor_user_id: int | None, action: str, resource_type: str, resource_id: str, metadata: dict[str, Any]) -> None:
        self.session.add(AuditLog(actor_user_id=actor_user_id, action=action, resource_type=resource_type, resource_id=resource_id, metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True)))


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, factory: async_sessionmaker[AsyncSession]): self.factory = factory; self.session: AsyncSession | None = None
    async def __aenter__(self):
        self.session = self.factory()
        self._content_versions = SQLAlchemyContentVersions(self.session)
        self._publication_pointers = SQLAlchemyPublicationPointers(self.session)
        self._outbox = SQLAlchemyOutbox(self.session); self._idempotency = SQLAlchemyIdempotency(self.session); self._audit = SQLAlchemyAudit(self.session)
        return self
    @property
    def content_versions(self): return self._content_versions
    @property
    def publication_pointers(self): return self._publication_pointers
    @property
    def outbox(self): return self._outbox
    @property
    def idempotency(self): return self._idempotency
    @property
    def audit(self): return self._audit
    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None: await self.commit()
        else: await self.rollback()
        await self.session.close()
        return None
    async def commit(self): await self.session.commit()
    async def rollback(self): await self.session.rollback()
