"""Provider-neutral contract guards for curriculum publication workflows.

These guards validate intent and state snapshots; persistence and dispatch remain
owned by the caller so the module is safe to exercise without PostgreSQL.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class GuardViolation(ValueError):
    """Raised when a requested lifecycle operation violates a contract."""


class ProcessingState(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class ReviewState(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VectorSyncState(StrEnum):
    VECTOR_PENDING = "VECTOR_PENDING"
    VECTOR_SYNCING = "VECTOR_SYNCING"
    VECTOR_SYNCED = "VECTOR_SYNCED"
    VECTOR_FAILED = "VECTOR_FAILED"


PROCESSING_TRANSITIONS: Mapping[str, frozenset[str]] = {
    ProcessingState.UPLOADED: frozenset({ProcessingState.PROCESSING, ProcessingState.FAILED, ProcessingState.QUARANTINED}),
    ProcessingState.PROCESSING: frozenset({ProcessingState.EXTRACTED, ProcessingState.FAILED, ProcessingState.QUARANTINED}),
    ProcessingState.EXTRACTED: frozenset({ProcessingState.VALIDATED, ProcessingState.FAILED, ProcessingState.QUARANTINED}),
    ProcessingState.VALIDATED: frozenset({ProcessingState.FAILED, ProcessingState.QUARANTINED}),
    ProcessingState.FAILED: frozenset(),
    ProcessingState.QUARANTINED: frozenset(),
}
REVIEW_TRANSITIONS: Mapping[str, frozenset[str]] = {
    ReviewState.DRAFT: frozenset({ReviewState.PENDING_REVIEW, ReviewState.REJECTED}),
    ReviewState.PENDING_REVIEW: frozenset({ReviewState.APPROVED, ReviewState.REJECTED}),
    ReviewState.APPROVED: frozenset({ReviewState.REJECTED}),
    ReviewState.REJECTED: frozenset(),
}
VECTOR_TRANSITIONS: Mapping[str, frozenset[str]] = {
    VectorSyncState.VECTOR_PENDING: frozenset({VectorSyncState.VECTOR_SYNCING, VectorSyncState.VECTOR_FAILED}),
    VectorSyncState.VECTOR_SYNCING: frozenset({VectorSyncState.VECTOR_SYNCED, VectorSyncState.VECTOR_FAILED}),
    VectorSyncState.VECTOR_FAILED: frozenset({VectorSyncState.VECTOR_PENDING}),
    VectorSyncState.VECTOR_SYNCED: frozenset({VectorSyncState.VECTOR_FAILED}),
}


def assert_transition(machine: str, current: str, target: str) -> None:
    tables = {"processing": PROCESSING_TRANSITIONS, "review": REVIEW_TRANSITIONS, "vector": VECTOR_TRANSITIONS}
    try:
        allowed = tables[machine][current]
    except (KeyError, TypeError) as exc:
        raise GuardViolation(f"unknown {machine} state: {current!r}") from exc
    if target not in allowed:
        raise GuardViolation(f"invalid {machine} transition: {current} -> {target}")


@dataclass(frozen=True)
class PublicationCandidate:
    version_id: int
    processing_state: str
    review_state: str
    vector_sync_state: str
    pipeline_digest: str | None
    approval_digest: str | None = None


def assert_publishable(candidate: PublicationCandidate, expected_digest: str | None = None) -> None:
    if candidate.version_id <= 0:
        raise GuardViolation("content version must be a persisted positive id")
    required = (ProcessingState.VALIDATED, ReviewState.APPROVED, VectorSyncState.VECTOR_SYNCED)
    actual = (candidate.processing_state, candidate.review_state, candidate.vector_sync_state)
    if actual != required:
        raise GuardViolation("publication requires VALIDATED + APPROVED + VECTOR_SYNCED")
    if not candidate.pipeline_digest:
        raise GuardViolation("publication requires a pipeline digest")
    if candidate.approval_digest is not None and candidate.approval_digest != candidate.pipeline_digest:
        raise GuardViolation("approval digest does not match content digest")
    if expected_digest is not None and expected_digest != candidate.pipeline_digest:
        raise GuardViolation("content digest changed during publication (CAS mismatch)")


def assert_pointer_cas(current_version_id: int | None, expected_version_id: int | None) -> None:
    if current_version_id != expected_version_id:
        raise GuardViolation("publication pointer compare-and-swap failed")


def assert_idempotent_request(existing_hash: str | None, request_hash: str) -> bool:
    """Return True for a safe replay; reject reuse of a key for new content."""
    if not request_hash:
        raise GuardViolation("request hash is required")
    if existing_hash is None:
        return False
    if existing_hash != request_hash:
        raise GuardViolation("idempotency key reused with a different request")
    return True

