from dataclasses import dataclass
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Classroom, TeacherProfile

@dataclass(frozen=True)
class TeacherClassScope:
    teacher_id: str
    tenant_id: str
    classroom_ids: frozenset[int]

def can_access_class(*, scope: TeacherClassScope, classroom_id: int, tenant_id: str) -> bool:
    return tenant_id == scope.tenant_id and classroom_id in scope.classroom_ids

def require_class(*, scope: TeacherClassScope, classroom_id: int, tenant_id: str) -> None:
    if not can_access_class(scope=scope, classroom_id=classroom_id, tenant_id=tenant_id):
        raise PermissionError("CLASS_SCOPE_DENIED")


async def resolve_teacher_scope(
    *, teacher_id: int, tenant_id: str | None, session: AsyncSession
) -> TeacherClassScope:
    """Resolve the teacher's persisted classroom scope, failing closed."""
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    profile = await session.scalar(
        select(TeacherProfile).where(
            TeacherProfile.teacher_id == teacher_id,
            TeacherProfile.tenant_id == tenant_id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=403, detail="Teacher scope denied")
    classroom_ids = await session.scalars(
        select(Classroom.id).where(
            Classroom.teacher_profile_id == profile.id,
            Classroom.tenant_id == tenant_id,
        )
    )
    return TeacherClassScope(str(teacher_id), tenant_id, frozenset(classroom_ids.all()))
