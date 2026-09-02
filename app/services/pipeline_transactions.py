"""Transactional persistence boundary for curriculum publication.

The module contains database-only orchestration. External I/O belongs to the
caller and must complete before this short transaction is opened.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    ContentVersion,
    IngestionIdempotencyKey,
    PublicationPointer,
    TransactionalOutboxEvent,
)
from app.services.pipeline_guards import (
    GuardViolation,
    PublicationCandidate,
    assert_idempotent_request,
    assert_publishable,
)


class ConflictError(RuntimeError):
    """The pointer changed since the caller read it."""


class InvalidStateError(RuntimeError):
    """The requested publication is not valid."""


@dataclass(frozen=True)
class PublicationResult:
    content_version_id: int
    event_id: str
    replayed: bool = False


async def publish_content_version(
    session: AsyncSession,
    *,
    content_version_id: int,
    expected_pointer_version: int | None,
    idempotency_key: str,
    request_hash: str,
    event_id: str,
    actor_user_id: int | None = None,
) -> PublicationResult:
    """Atomically publish a prepared version and record its side effects.

    State, pointer, approval evidence, outbox event, idempotency record and
    audit log are committed together. No network or provider call is made.
    """
    async with session.begin():
        idem = await session.scalar(
            select(IngestionIdempotencyKey)
            .where(IngestionIdempotencyKey.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if idem is not None:
            try:
                replayed = assert_idempotent_request(idem.request_hash, request_hash)
            except GuardViolation as exc:
                raise InvalidStateError(str(exc)) from exc
            if replayed:
                return PublicationResult(idem.source_document_id or 0, event_id, replayed=True)

        version = await session.scalar(
            select(ContentVersion)
            .where(ContentVersion.id == content_version_id)
            .with_for_update()
        )
        if version is None:
            raise InvalidStateError("content version does not exist")
        candidate = PublicationCandidate(
            version_id=version.id,
            processing_state=version.processing_state,
            review_state=version.review_state,
            vector_sync_state=version.vector_sync_state,
            pipeline_digest=version.pipeline_digest,
            approval_digest=version.pipeline_digest,
        )
        try:
            assert_publishable(candidate)
        except GuardViolation as exc:
            raise InvalidStateError(str(exc)) from exc

        pointer = await session.scalar(
            select(PublicationPointer)
            .where(PublicationPointer.source_document_id == version.source_document_id)
            .with_for_update()
        )
        current = pointer.version if pointer is not None else None
        if expected_pointer_version is not None and current != expected_pointer_version:
            raise ConflictError("publication pointer compare-and-swap failed")
        if pointer is None:
            pointer = PublicationPointer(
                source_document_id=version.source_document_id,
                content_version_id=version.id,
                version=1,
            )
            session.add(pointer)
        else:
            pointer.content_version_id = version.id
            pointer.version += 1

        payload = json.dumps(
            {"content_version_id": version.id, "pipeline_digest": version.pipeline_digest},
            ensure_ascii=False,
            sort_keys=True,
        )
        session.add(
            TransactionalOutboxEvent(
                event_id=event_id,
                event_type="CONTENT_VERSION_PUBLISHED",
                aggregate_type="source_document",
                aggregate_id=str(version.source_document_id),
                payload_json=payload,
            )
        )
        if idem is None:
            session.add(
                IngestionIdempotencyKey(
                    idempotency_key=idempotency_key,
                    source_document_id=version.source_document_id,
                    request_hash=request_hash,
                    status="COMPLETED",
                    response_json=payload,
                )
            )
        session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action="CONTENT_VERSION_PUBLISHED",
                resource_type="content_version",
                resource_id=str(version.id),
                metadata_json=payload,
            )
        )
        return PublicationResult(version.id, event_id)

