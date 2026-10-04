"""Validation primitives for the versioned submission transaction service.

The caller must establish authenticated ownership and tenant context before
looking up a replay. No client-provided identity is accepted by these helpers.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assignment, StudentSubmission, SubmissionReview, SubmissionRevision


class SubmissionRevisionError(ValueError):
    """A request cannot be applied to the authorized submission."""


class SubmissionRevisionConflict(SubmissionRevisionError):
    """An idempotency key was already used for different content."""


def validate_idempotency_key(value: str) -> str:
    """Reject ambiguous keys rather than silently normalizing client identity."""
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise SubmissionRevisionError("idempotency key must contain 1-128 characters")
    if value != value.strip() or any(ord(character) < 32 for character in value):
        raise SubmissionRevisionError("idempotency key contains invalid whitespace")
    return value


def encode_submission(content: dict[str, Any]) -> tuple[str, str]:
    """Return canonical JSON and a versioned fingerprint, never a dedup key.

    Identical content under distinct client keys remains a deliberate resubmit.
    Non-finite numbers cannot be encoded into a valid JSON snapshot.
    """
    if not isinstance(content, dict):
        raise SubmissionRevisionError("submission content must be an object")
    try:
        payload = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        fingerprint = hashlib.sha256(("submission-v1\n" + payload).encode("utf-8")).hexdigest()
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SubmissionRevisionError("submission content must be valid JSON") from exc
    return payload, fingerprint


@dataclass(frozen=True)
class RevisionResult:
    submission: StudentSubmission
    revision: SubmissionRevision
    replayed: bool


async def create_revision(
    session: AsyncSession,
    *,
    assignment_id: int,
    student_profile_id: int,
    tenant_id: str,
    idempotency_key: str,
    content: dict[str, Any],
) -> RevisionResult:
    """Create/replay inside the caller's authorized, tenant-scoped transaction.

    The route must resolve membership/entitlement and the student profile from
    the authenticated principal. This function never commits the transaction.
    PostgreSQL parent locks serialize numbering and replay resolution.
    """
    if not session.in_transaction():
        raise SubmissionRevisionError("active transaction required")
    key = validate_idempotency_key(idempotency_key)
    payload, fingerprint = encode_submission(content)
    parent_query = select(StudentSubmission).where(
        StudentSubmission.assignment_id == assignment_id,
        StudentSubmission.student_id == student_profile_id,
        StudentSubmission.tenant_id == tenant_id,
    ).with_for_update()
    parent = await session.scalar(parent_query)
    if parent is None:
        try:
            async with session.begin_nested():
                parent = StudentSubmission(
                    assignment_id=assignment_id,
                    student_id=student_profile_id,
                    tenant_id=tenant_id,
                    status="NOT_SUBMITTED",
                    revision=1,
                )
                session.add(parent)
                await session.flush()
        except IntegrityError:
            # A concurrent first submission may have claimed the parent. Do not
            # recover unrelated FK/check errors or reveal an invisible parent.
            parent = await session.scalar(parent_query)
            if parent is None:
                raise

    existing = await session.scalar(select(SubmissionRevision).where(
        SubmissionRevision.submission_id == parent.id,
        SubmissionRevision.tenant_id == tenant_id,
        SubmissionRevision.submit_idempotency_key == key,
    ))
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise SubmissionRevisionConflict("idempotency key conflicts with content")
        return RevisionResult(parent, existing, True)

    latest = await session.scalar(select(func.max(SubmissionRevision.revision_no)).where(
        SubmissionRevision.submission_id == parent.id,
        SubmissionRevision.tenant_id == tenant_id,
    ))
    now = datetime.now(UTC)
    revision = SubmissionRevision(
        submission_id=parent.id, tenant_id=tenant_id,
        revision_no=(latest or 0) + 1, content_json=payload,
        submitted_at=now, provenance="SUBMITTED",
        submit_idempotency_key=key, request_fingerprint=fingerprint,
    )
    session.add(revision)
    await session.flush()
    parent.current_revision_id = revision.id
    parent.revision = revision.revision_no
    parent.content_json = payload
    parent.submitted_at = now
    parent.status = "SUBMITTED"
    await session.flush()
    return RevisionResult(parent, revision, False)


async def bind_review(
    session: AsyncSession,
    *,
    submission_id: int,
    revision_id: int,
    teacher_user_id: int,
    tenant_id: str,
    review_status: str,
    score: float | None,
    feedback: str | None,
) -> tuple[SubmissionReview, bool]:
    """Review an owned exact revision; serialize against parent resubmissions.

    Updates to one revision use serialized last-writer-wins semantics. An
    explicit historical review is allowed, but cannot review the current child.
    Tenant context must already be established by the authenticated route.
    """
    if not session.in_transaction():
        raise SubmissionRevisionError("active transaction required")
    parent = await session.scalar(
        select(StudentSubmission)
        .join(Assignment, Assignment.id == StudentSubmission.assignment_id)
        .where(
            StudentSubmission.id == submission_id,
            StudentSubmission.tenant_id == tenant_id,
            Assignment.tenant_id == tenant_id,
            Assignment.teacher_id == teacher_user_id,
        )
        .with_for_update(of=StudentSubmission)
    )
    if parent is None:
        raise SubmissionRevisionError("submission not found")
    revision = await session.scalar(select(SubmissionRevision).where(
        SubmissionRevision.id == revision_id,
        SubmissionRevision.submission_id == parent.id,
        SubmissionRevision.tenant_id == tenant_id,
    ))
    if revision is None or parent.status == "NOT_SUBMITTED":
        raise SubmissionRevisionError("submitted revision not found")
    if revision.provenance == "BASELINE_BACKFILL" and revision.submitted_at is None:
        raise SubmissionRevisionError("baseline has no submitted event")
    review = await session.scalar(select(SubmissionReview).where(
        SubmissionReview.submission_revision_id == revision.id,
        SubmissionReview.submission_id == parent.id,
        SubmissionReview.tenant_id == tenant_id,
    ))
    if review is None:
        review = SubmissionReview(
            submission_id=parent.id,
            submission_revision_id=revision.id,
            tenant_id=tenant_id,
            association_provenance="EXACT_REVISION",
        )
        session.add(review)
    # An explicit new review evaluates the identified snapshot. Legacy
    # association provenance stays unchanged until this deliberate action.
    review.association_provenance = "EXACT_REVISION"
    review.review_status = review_status
    review.score = score
    review.teacher_feedback = feedback
    review.reviewed_by = teacher_user_id
    review.reviewed_at = datetime.now(UTC)
    is_current = parent.current_revision_id == revision.id
    if is_current:
        parent.status = "REVIEWED"
    await session.flush()
    return review, is_current


async def read_feedback(
    session: AsyncSession,
    *,
    submission_id: int,
    student_profile_id: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Return only the authenticated owner's history with explicit provenance.

    Caller resolves the profile from the authenticated user and establishes
    transaction-local tenant context before invoking this function.
    """
    parent = await session.scalar(select(StudentSubmission).where(
        StudentSubmission.id == submission_id,
        StudentSubmission.student_id == student_profile_id,
        StudentSubmission.tenant_id == tenant_id,
    ))
    if parent is None:
        raise SubmissionRevisionError("submission not found")
    rows = (await session.execute(
        select(SubmissionRevision, SubmissionReview)
        .outerjoin(SubmissionReview, and_(
            SubmissionReview.submission_revision_id == SubmissionRevision.id,
            SubmissionReview.submission_id == SubmissionRevision.submission_id,
            SubmissionReview.tenant_id == SubmissionRevision.tenant_id,
        ))
        .where(
            SubmissionRevision.submission_id == parent.id,
            SubmissionRevision.tenant_id == tenant_id,
        )
        .order_by(SubmissionRevision.revision_no)
    )).all()
    return {
        "submission_id": parent.id,
        "status": parent.status,
        "current_revision_id": parent.current_revision_id,
        "revisions": [
            {
                "submission_revision_id": revision.id,
                "revision": revision.revision_no,
                "is_current": revision.id == parent.current_revision_id,
                "provenance": revision.provenance,
                "submitted_at": revision.submitted_at.isoformat() if revision.submitted_at else None,
                "review": {
                    "status": review.review_status,
                    "score": review.score,
                    "feedback": review.teacher_feedback,
                    "association_provenance": review.association_provenance,
                } if review else None,
            }
            for revision, review in rows
        ],
    }
