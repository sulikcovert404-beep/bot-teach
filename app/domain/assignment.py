"""Provider-neutral Assignment V1 contract and permission policies.

This module intentionally contains no persistence, HTTP, worker, or provider code.
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class AssignmentStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    PAST_DUE = "PAST_DUE"
    CLOSED = "CLOSED"


class SubmissionStatus(StrEnum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    teacher_id: str
    classroom_id: str
    tenant_id: str
    status: AssignmentStatus = AssignmentStatus.DRAFT
    publish_at: datetime | None = None
    due_at: datetime | None = None
    close_at: datetime | None = None


@dataclass(frozen=True)
class AssignmentSnapshot:
    assignment_id: str
    snapshot_version: int
    content_references: tuple[str, ...]
    payload_digest: str


@dataclass(frozen=True)
class AssignmentTarget:
    assignment_id: str
    classroom_id: str
    tenant_id: str


@dataclass(frozen=True)
class StudentSubmission:
    assignment_id: str
    student_id: str
    tenant_id: str
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    submitted_at: datetime | None = None
    revision: int = 1


@dataclass(frozen=True)
class SubmissionReview:
    assignment_id: str
    student_id: str
    reviewer_id: str
    review_status: str
    score: float | None = None
    feedback: str | None = None


def assignment_status_at(assignment: Assignment, *, now: datetime) -> AssignmentStatus:
    """Derive time-sensitive state without mutating or requiring a scheduler."""
    if assignment.status is AssignmentStatus.DRAFT:
        return AssignmentStatus.DRAFT
    if assignment.close_at and now >= _utc(assignment.close_at):
        return AssignmentStatus.CLOSED
    if assignment.due_at and now >= _utc(assignment.due_at):
        return AssignmentStatus.PAST_DUE
    return assignment.status


def can_teacher_manage(*, teacher_id: str, assignment: Assignment, tenant_id: str, classroom_ids: set[str]) -> bool:
    return teacher_id == assignment.teacher_id and tenant_id == assignment.tenant_id and assignment.classroom_id in classroom_ids


def can_student_read(*, student_tenant_id: str, assignment: Assignment, enrolled: bool, entitled: bool, now: datetime) -> bool:
    return (student_tenant_id == assignment.tenant_id and enrolled and entitled
            and assignment_status_at(assignment, now=now) is not AssignmentStatus.DRAFT)


def can_student_submit(*, student_tenant_id: str, assignment: Assignment, enrolled: bool, entitled: bool, now: datetime) -> bool:
    if not can_student_read(student_tenant_id=student_tenant_id, assignment=assignment, enrolled=enrolled, entitled=entitled, now=now):
        return False
    return assignment.close_at is None or now < _utc(assignment.close_at)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
