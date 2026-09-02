"""Provider-neutral command/query contracts for curriculum content lifecycle.

This module deliberately contains no OCR, parser, worker, vector-store, or HTTP
client code.  It provides the stable service boundary that adapters can call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class PipelineError(RuntimeError):
    code = "PIPELINE_ERROR"
    retryable = False


class AuthorizationError(PipelineError):
    code = "AUTHORIZATION_ERROR"


class InvalidStateError(PipelineError):
    code = "INVALID_STATE"


class DigestMismatchError(PipelineError):
    code = "DIGEST_MISMATCH"


class CASConflictError(PipelineError):
    code = "CAS_CONFLICT"
    retryable = True


class RetryableProcessingError(PipelineError):
    code = "PROCESSING_RETRYABLE"
    retryable = True


class ProcessingState(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    VECTOR_SYNCED = "VECTOR_SYNCED"


class ReviewState(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class JobState(StrEnum):
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Actor:
    user_id: int | None
    role: str
    tenant_id: str | None = None


@dataclass(frozen=True)
class CommandContext:
    actor: Actor
    idempotency_key: str
    expected_version: int | None = None
    reason: str | None = None
    request_hash: str | None = None


@dataclass(frozen=True)
class ContentVersionSnapshot:
    content_version_id: int
    source_document_id: int
    version: int
    processing_state: ProcessingState
    review_state: ReviewState
    vector_sync_state: ProcessingState
    digest: str | None
    retired: bool = False


@dataclass(frozen=True)
class JobReceipt:
    job_id: str
    content_version_id: int
    status: JobState


@dataclass(frozen=True)
class CommandReceipt:
    command_id: str
    status: str
    result: Any
    event_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


ROLE_RULES: dict[str, frozenset[str]] = {
    "create": frozenset({"CONTENT_ADMIN", "SUPER_ADMIN"}),
    "submit": frozenset({"CONTENT_ADMIN", "PIPELINE" , "SUPER_ADMIN"}),
    "validate": frozenset({"PIPELINE", "SUPER_ADMIN"}),
    "approve": frozenset({"REVIEWER", "SUPER_ADMIN"}),
    "vector_sync": frozenset({"PIPELINE", "SUPER_ADMIN"}),
    "publish": frozenset({"CONTENT_ADMIN", "PUBLISHER", "SUPER_ADMIN"}),
    "retire": frozenset({"CONTENT_ADMIN", "PUBLISHER", "SUPER_ADMIN"}),
}


def require_role(actor: Actor, operation: str) -> None:
    if actor.role not in ROLE_RULES[operation]:
        raise AuthorizationError(f"role {actor.role!r} cannot perform {operation}")


class CurriculumPipelineService:
    """Small reference service; persistence adapters can implement the same contract."""

    def __init__(self) -> None:
        self._versions: dict[int, ContentVersionSnapshot] = {}
        self._jobs: dict[str, JobReceipt] = {}
        self._receipts: dict[str, CommandReceipt] = {}
        self._request_hashes: dict[str, str | None] = {}
        self._next_id = 1

    def _receipt(self, ctx: CommandContext, result: Any) -> CommandReceipt:
        existing = self._receipts.get(ctx.idempotency_key)
        if existing is not None:
            if self._request_hashes[ctx.idempotency_key] != ctx.request_hash:
                raise PipelineError("idempotency key was reused for a different request")
            return existing
        receipt = CommandReceipt(str(uuid4()), "COMMITTED", result)
        self._receipts[ctx.idempotency_key] = receipt
        self._request_hashes[ctx.idempotency_key] = ctx.request_hash
        return receipt

    def create_content_version(self, ctx: CommandContext, source_document_id: int, digest: str) -> CommandReceipt:
        require_role(ctx.actor, "create")
        if not digest:
            raise DigestMismatchError("content digest is required")
        version = ContentVersionSnapshot(self._next_id, source_document_id, 1, ProcessingState.UPLOADED,
                                         ReviewState.DRAFT, ProcessingState.UPLOADED, digest)
        self._next_id += 1
        self._versions[version.content_version_id] = version
        return self._receipt(ctx, version)

    def submit_processing_job(self, ctx: CommandContext, content_version_id: int) -> CommandReceipt:
        require_role(ctx.actor, "submit")
        version = self._get(content_version_id)
        job = JobReceipt(str(uuid4()), version.content_version_id, JobState.ACCEPTED)
        self._jobs[job.job_id] = job
        return self._receipt(ctx, job)

    def validate_content(self, ctx: CommandContext, content_version_id: int) -> CommandReceipt:
        require_role(ctx.actor, "validate")
        version = self._get(content_version_id)
        self._expect_version(ctx, version)
        if version.retired or version.processing_state is not ProcessingState.UPLOADED:
            raise InvalidStateError("content must be uploaded and active before validation")
        return self._replace(ctx, version, processing_state=ProcessingState.VALIDATED)

    def approve_content(self, ctx: CommandContext, content_version_id: int, digest: str) -> CommandReceipt:
        require_role(ctx.actor, "approve")
        version = self._get(content_version_id)
        self._expect_version(ctx, version)
        if digest != version.digest:
            raise DigestMismatchError("approval digest does not match content digest")
        if version.processing_state is not ProcessingState.VALIDATED:
            raise InvalidStateError("content must be validated before approval")
        return self._replace(ctx, version, review_state=ReviewState.APPROVED)

    def mark_vector_synced(self, ctx: CommandContext, content_version_id: int, digest: str) -> CommandReceipt:
        require_role(ctx.actor, "vector_sync")
        version = self._get(content_version_id)
        self._expect_version(ctx, version)
        if digest != version.digest:
            raise DigestMismatchError("vector sync digest does not match content digest")
        if version.review_state is not ReviewState.APPROVED:
            raise InvalidStateError("content must be approved before vector sync")
        return self._replace(ctx, version, vector_sync_state=ProcessingState.VECTOR_SYNCED)

    def publish_content_version(self, ctx: CommandContext, content_version_id: int) -> CommandReceipt:
        require_role(ctx.actor, "publish")
        version = self._get(content_version_id)
        self._expect_version(ctx, version)
        if version.processing_state is not ProcessingState.VALIDATED or version.review_state is not ReviewState.APPROVED or version.vector_sync_state is not ProcessingState.VECTOR_SYNCED:
            raise InvalidStateError("publish gate requires VALIDATED, APPROVED, VECTOR_SYNCED, and digest match")
        return self._receipt(ctx, version)

    def retire_content_version(self, ctx: CommandContext, content_version_id: int) -> CommandReceipt:
        require_role(ctx.actor, "retire")
        version = self._get(content_version_id)
        self._expect_version(ctx, version)
        return self._replace(ctx, version, retired=True)

    def get_job(self, job_id: str) -> JobReceipt:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise InvalidStateError("processing job does not exist") from exc

    def get_content_status(self, content_version_id: int) -> ContentVersionSnapshot:
        return self._get(content_version_id)

    def _get(self, content_version_id: int) -> ContentVersionSnapshot:
        try:
            return self._versions[content_version_id]
        except KeyError as exc:
            raise InvalidStateError("content version does not exist") from exc

    @staticmethod
    def _expect_version(ctx: CommandContext, version: ContentVersionSnapshot) -> None:
        if ctx.expected_version is not None and ctx.expected_version != version.version:
            raise CASConflictError("content version changed")

    def _replace(self, ctx: CommandContext, version: ContentVersionSnapshot, **changes: Any) -> CommandReceipt:
        updated = ContentVersionSnapshot(version.content_version_id, version.source_document_id, version.version + 1,
                                         changes.get("processing_state", version.processing_state),
                                         changes.get("review_state", version.review_state),
                                         changes.get("vector_sync_state", version.vector_sync_state),
                                         version.digest, changes.get("retired", version.retired))
        self._versions[version.content_version_id] = updated
        return self._receipt(ctx, updated)
