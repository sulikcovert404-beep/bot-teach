"""Application boundary for the bounded class enrollment database operations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ClassEnrollmentResult:
    status: str
    classroom_id: int
    student_user_id: int
    tenant_id: str


class ClassEnrollmentDenied(PermissionError):
    """The authenticated actor or target is outside the allowed school scope."""


async def _operate(
    session: AsyncSession,
    function: str,
    *,
    actor_id: int,
    actor_role: str,
    classroom_id: int,
    student_user_id: int,
) -> ClassEnrollmentResult:
    try:
        result = await session.scalar(
            text(f"SELECT public.{function}(:actor_id,:actor_role,:classroom_id,:student_user_id)"),
            {
                "actor_id": actor_id,
                "actor_role": actor_role,
                "classroom_id": classroom_id,
                "student_user_id": student_user_id,
            },
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if "class_enrollment_denied" in str(getattr(exc, "orig", exc)):
            raise ClassEnrollmentDenied from exc
        raise
    if isinstance(result, str):
        import json

        result = json.loads(result)
    return ClassEnrollmentResult(
        status=str(result["status"]),
        classroom_id=int(result["classroom_id"]),
        student_user_id=int(result["student_user_id"]),
        tenant_id=str(result["tenant_id"]),
    )


async def enroll_class_student(
    session: AsyncSession, *, actor_id: int, actor_role: str,
    classroom_id: int, student_user_id: int,
) -> ClassEnrollmentResult:
    return await _operate(
        session, "enroll_class_student", actor_id=actor_id, actor_role=actor_role,
        classroom_id=classroom_id, student_user_id=student_user_id,
    )


async def remove_class_student(
    session: AsyncSession, *, actor_id: int, actor_role: str,
    classroom_id: int, student_user_id: int,
) -> ClassEnrollmentResult:
    return await _operate(
        session, "remove_class_student", actor_id=actor_id, actor_role=actor_role,
        classroom_id=classroom_id, student_user_id=student_user_id,
    )
