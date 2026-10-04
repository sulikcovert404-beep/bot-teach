"""Canonical SCHOOL_ADMIN class enrollment resources."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.security.dependencies import require_roles
from app.services.class_enrollment import (
    ClassEnrollmentDenied,
    enroll_class_student,
    remove_class_student,
)

router = APIRouter(prefix="/school-admin/classrooms", tags=["class-enrollment"])


class EnrollmentRequest(BaseModel):
    student_user_id: int = Field(gt=0)


def _actor_id(subject: str) -> int:
    try:
        value = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    if value <= 0:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    return value


def _result_payload(result) -> dict[str, object]:
    return {
        "status": result.status,
        "classroom_id": result.classroom_id,
        "student_user_id": result.student_user_id,
        "tenant_id": result.tenant_id,
    }


@router.post("/{classroom_id}/students", status_code=status.HTTP_201_CREATED)
async def enroll_student(
    classroom_id: int,
    payload: EnrollmentRequest,
    subject: str = Depends(require_roles("SCHOOL_ADMIN")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    try:
        result = await enroll_class_student(
            session, actor_id=_actor_id(subject), actor_role="SCHOOL_ADMIN",
            classroom_id=classroom_id, student_user_id=payload.student_user_id,
        )
    except ClassEnrollmentDenied as exc:
        raise HTTPException(status_code=403, detail="Class enrollment denied") from exc
    return _result_payload(result)


@router.delete("/{classroom_id}/students/{student_user_id}")
async def remove_student(
    classroom_id: int,
    student_user_id: int,
    subject: str = Depends(require_roles("SCHOOL_ADMIN")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    try:
        result = await remove_class_student(
            session, actor_id=_actor_id(subject), actor_role="SCHOOL_ADMIN",
            classroom_id=classroom_id, student_user_id=student_user_id,
        )
    except ClassEnrollmentDenied as exc:
        raise HTTPException(status_code=403, detail="Class enrollment denied") from exc
    return _result_payload(result)
