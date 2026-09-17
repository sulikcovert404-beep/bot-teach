"""Canonical, tenant-scoped application service for persisted exam attempts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Assignment,
    ClassMembership,
    Classroom,
    Exam,
    ExamAttempt,
    ExamResult,
    StudentProfile,
)


class ExamAccessError(Exception):
    """Raised for any unauthorized or invalid exam operation."""


async def start_attempt(session: AsyncSession, *, assignment_id: int, student_id: int, tenant_id: str) -> ExamAttempt:
    # Lock the assignment row while allocating the next attempt number.  The
    # unique constraint remains the final guard, but the row lock prevents two
    # concurrent requests from selecting the same max(attempt_no).
    assignment = await session.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.tenant_id == tenant_id, Assignment.exam_id.is_not(None)).with_for_update())
    if assignment is None or assignment.status != "PUBLISHED":
        raise ExamAccessError("assignment unavailable")
    now = datetime.now(timezone.utc)
    if assignment.publish_at is not None and now < assignment.publish_at.replace(tzinfo=timezone.utc):
        raise ExamAccessError("assignment not yet available")
    if assignment.due_at is not None and now > assignment.due_at.replace(tzinfo=timezone.utc):
        raise ExamAccessError("assignment window closed")
    if assignment.close_at is not None and now >= assignment.close_at.replace(tzinfo=timezone.utc):
        raise ExamAccessError("assignment closed")
    profile = await session.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))
    membership = await session.scalar(
        select(ClassMembership.id)
        .join(Classroom, Classroom.id == ClassMembership.classroom_id)
        .where(
            ClassMembership.classroom_id == assignment.classroom_id,
            ClassMembership.student_id == (profile.id if profile else -1),
            Classroom.tenant_id == tenant_id,
        )
    )
    if profile is None or membership is None:
        raise ExamAccessError("student is not an active classroom member")
    exam = await session.scalar(
        select(Exam)
        .options(selectinload(Exam.questions))
        .where(Exam.id == assignment.exam_id, Exam.tenant_id == tenant_id)
    )
    if exam is None:
        raise ExamAccessError("exam unavailable")
    latest = await session.scalar(select(func.max(ExamAttempt.attempt_no)).where(ExamAttempt.assignment_id == assignment_id, ExamAttempt.student_id == student_id, ExamAttempt.tenant_id == tenant_id))
    attempt = ExamAttempt(tenant_id=tenant_id, assignment_id=assignment_id, student_id=student_id, attempt_no=(latest or 0) + 1, question_snapshot=json.dumps([{"id": q.id, "prompt": q.prompt, "options": q.options.split("\n"), "correct_option": q.correct_option, "position": q.position} for q in sorted(exam.questions, key=lambda x: x.position)], ensure_ascii=False, sort_keys=True))
    session.add(attempt)
    await session.flush()
    return attempt


async def save_answers(session: AsyncSession, *, attempt_id: int, student_id: int, tenant_id: str, answers: dict[str, Any]) -> ExamAttempt:
    attempt = await session.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.student_id == student_id, ExamAttempt.tenant_id == tenant_id))
    if attempt is None or attempt.status not in {"STARTED", "IN_PROGRESS"}:
        raise ExamAccessError("attempt unavailable")
    attempt.answer_payload = json.dumps(answers, ensure_ascii=False, sort_keys=True)
    attempt.status = "IN_PROGRESS"
    attempt.last_saved_at = datetime.now(timezone.utc)
    return attempt


async def submit_attempt(session: AsyncSession, *, attempt_id: int, student_id: int, tenant_id: str) -> ExamResult:
    attempt = await session.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.student_id == student_id, ExamAttempt.tenant_id == tenant_id))
    if attempt is None or attempt.status not in {"STARTED", "IN_PROGRESS", "SUBMITTED", "GRADED"}:
        raise ExamAccessError("attempt unavailable")
    assignment = await session.scalar(select(Assignment).where(Assignment.id == attempt.assignment_id, Assignment.tenant_id == tenant_id))
    now = datetime.now(timezone.utc)
    if assignment is None or (assignment.publish_at is not None and now < assignment.publish_at.replace(tzinfo=timezone.utc)):
        raise ExamAccessError("assignment not yet available")
    if assignment.due_at is not None and now > assignment.due_at.replace(tzinfo=timezone.utc):
        raise ExamAccessError("assignment window closed")
    if assignment.close_at is not None and now >= assignment.close_at.replace(tzinfo=timezone.utc):
        raise ExamAccessError("assignment closed")
    existing = await session.scalar(select(ExamResult).where(ExamResult.attempt_id == attempt.id, ExamResult.tenant_id == tenant_id))
    if existing is not None:
        return existing
    snapshot = json.loads(attempt.question_snapshot)
    answers = json.loads(attempt.answer_payload or "{}")
    score = sum(1 for q in snapshot if answers.get(str(q["id"])) == q.get("correct_option"))
    result = ExamResult(tenant_id=tenant_id, attempt_id=attempt.id, score=float(score), max_score=float(len(snapshot)), grading_status="GRADED", grading_source="server", graded_at=datetime.now(timezone.utc))
    session.add(result)
    attempt.status = "GRADED"
    attempt.submitted_at = datetime.now(timezone.utc)
    await session.flush()
    return result
