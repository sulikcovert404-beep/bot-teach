import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    ClassMembership,
    Classroom,
    SchoolTenant,
    StudentProfile,
    TeacherProfile,
    User,
)


@pytest.mark.asyncio
async def test_credential_free_school_lifecycle_fixture_and_isolation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all([
            SchoolTenant(tenant_id="pilot-a", school_name="Pilot A"),
            SchoolTenant(tenant_id="pilot-b", school_name="Pilot B"),
            User(id=100, username="admin-a", role="SCHOOL_ADMIN"),
            User(id=101, username="teacher-a", role="TEACHER"),
            User(id=102, username="student-a", role="STUDENT"),
        ])
        await session.flush()
        teacher = TeacherProfile(teacher_id=101, tenant_id="pilot-a")
        student = StudentProfile(student_id=102)
        session.add_all([teacher, student])
        await session.flush()
        classroom = Classroom(classroom_key="class-a", tenant_id="pilot-a", teacher_profile_id=teacher.id)
        session.add(classroom)
        await session.flush()
        session.add(ClassMembership(classroom_id=classroom.id, student_id=student.id))
        await session.commit()

        assert await session.scalar(select(SchoolTenant).where(SchoolTenant.tenant_id == "pilot-a"))
        assert await session.scalar(select(TeacherProfile).where(TeacherProfile.teacher_id == 101, TeacherProfile.tenant_id == "pilot-a"))
        assert await session.scalar(select(ClassMembership).where(ClassMembership.classroom_id == classroom.id, ClassMembership.student_id == student.id))
        assert await session.scalar(select(Classroom).where(Classroom.id == classroom.id, Classroom.tenant_id == "pilot-b")) is None
        assert await session.scalar(select(ClassMembership).where(ClassMembership.classroom_id == classroom.id, ClassMembership.student_id != student.id)) is None
    await engine.dispose()
