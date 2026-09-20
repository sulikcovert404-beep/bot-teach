from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClassMembership, Classroom, SchoolTenant


class SchoolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, school_name: str) -> SchoolTenant:
        school = SchoolTenant(tenant_id=tenant_id, school_name=school_name)
        self.session.add(school)
        await self.session.flush()
        return school


class ClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, classroom_key: str, tenant_id: str, teacher_profile_id: int) -> Classroom:
        classroom = Classroom(classroom_key=classroom_key, tenant_id=tenant_id, teacher_profile_id=teacher_profile_id)
        self.session.add(classroom)
        await self.session.flush()
        return classroom

    async def get_for_tenant(self, classroom_id: int, tenant_id: str) -> Classroom | None:
        return await self.session.scalar(select(Classroom).where(Classroom.id == classroom_id, Classroom.tenant_id == tenant_id))


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, classroom_id: int, student_id: int) -> ClassMembership:
        membership = ClassMembership(classroom_id=classroom_id, student_id=student_id)
        self.session.add(membership)
        await self.session.flush()
        return membership
