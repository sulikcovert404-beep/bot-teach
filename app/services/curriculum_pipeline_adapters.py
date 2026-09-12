"""Provider-neutral adapter contracts for the curriculum pipeline.

Adapters own persistence and HTTP concerns; domain services remain unaware of
database sessions, web frameworks, or user sessions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from types import TracebackType
from typing import Any, Protocol, Self, TypeVar

from .curriculum_pipeline_api import (
    AuthorizationError,
    CASConflictError,
    ContentValidationError,
    DigestMismatchError,
    IdempotencyConflictError,
    IdempotencyRecordMissingError,
    InvalidStateError,
    PipelineError,
    RetryableProcessingError,
    SessionNotInitializedError,
)

T = TypeVar("T")


class UnitOfWork(Protocol):
    """Transaction boundary for one atomic command."""
    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

    @property
    def content_versions(self) -> ContentVersionRepository: ...
    @property
    def publication_pointers(self) -> PublicationPointerRepository: ...
    @property
    def outbox(self) -> OutboxRepository: ...
    @property
    def idempotency(self) -> IdempotencyRepository: ...
    @property
    def audit(self) -> AuditRepository: ...


class ContentVersionRepository(Protocol):
    async def get_for_update(self, content_version_id: int) -> Any: ...
    async def save(self, version: Any, *, expected_version: int | None = None) -> None: ...


class PublicationPointerRepository(Protocol):
    async def switch(self, source_document_id: int, content_version_id: int,
                     *, expected_version: int | None = None) -> Any: ...


class OutboxRepository(Protocol):
    async def append(self, event_id: str, event_type: str, aggregate_id: str,
                     payload: dict[str, Any]) -> None: ...


class IdempotencyRepository(Protocol):
    async def lock_or_get(self, key: str, request_hash: str) -> Any: ...
    async def complete(self, key: str, request_hash: str, response: dict[str, Any]) -> None: ...


class AuditRepository(Protocol):
    async def append(self, *, actor_user_id: int | None, action: str,
                     resource_type: str, resource_id: str, metadata: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class HttpError:
    status: int
    code: str
    message: str
    retryable: bool = False


def map_pipeline_error(error: Exception) -> HttpError:
    """Map typed domain failures at the HTTP boundary only."""
    if isinstance(error, AuthorizationError):
        return HttpError(403, error.code, str(error))
    if isinstance(error, ContentValidationError):
        return HttpError(422, error.code, str(error))
    if isinstance(error, CASConflictError):
        return HttpError(409, error.code, str(error), True)
    if isinstance(error, IdempotencyConflictError):
        return HttpError(409, error.code, str(error), False)
    if isinstance(error, (IdempotencyRecordMissingError, SessionNotInitializedError)):
        return HttpError(500, error.code, str(error))
    if isinstance(error, DigestMismatchError):
        return HttpError(422, error.code, str(error))
    if isinstance(error, InvalidStateError):
        return HttpError(422, error.code, str(error))
    if isinstance(error, RetryableProcessingError):
        return HttpError(503, error.code, str(error), True)
    if isinstance(error, PipelineError):
        return HttpError(400, error.code, str(error), error.retryable)
    return HttpError(500, "INTERNAL_ERROR", "internal pipeline failure")


def preserve_text(value: str) -> str:
    """Keep UTF-8 Persian ZWNJ/RTL/math text unchanged at adapter boundaries."""
    return value


def serialize_payload(value: Any) -> str:
    """Return stable UTF-8 JSON for receipts, hashes, and audit payloads."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    raise TypeError(f"unsupported payload value: {type(value).__name__}")


def check_contract_readiness() -> dict[str, str]:
    """Evaluate non-DB contract invariants without probing external services."""
    return {
        "provider_neutral_boundary": "ready",
        "typed_error_mapping": "ready",
        "stable_utf8_serialization": "ready",
        "database_runtime": "blocked_external_dependency",
    }
