import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    ClassMembership,
    Classroom,
    SchoolAdminMembership,
    SchoolTenant,
    StudentProfile,
    TeacherProfile,
    User,
)


@pytest.mark.asyncio
async def test_persisted_retrieval_across_sessions_and_restarts(tmp_path):
    db_file = tmp_path / "test_persistence.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    
    # --- PHASE 1: Seed data and completely dispose engine ---
    engine1 = create_async_engine(db_url)
    async with engine1.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    factory1 = async_sessionmaker(engine1, expire_on_commit=False)
    async with factory1() as session:
        t1 = SchoolTenant(tenant_id="tenant-persisted-1", school_name="دبیرستان ماندگار")
        admin = User(telegram_user_id=777, username="persisted_admin", role="SCHOOL_ADMIN")
        teacher = User(telegram_user_id=888, username="persisted_teacher", role="TEACHER")
        student = User(telegram_user_id=999, username="persisted_student", role="STUDENT")
        session.add_all([t1, admin, teacher, student])
        await session.commit()
        
        mem_admin = SchoolAdminMembership(user_id=admin.id, tenant_id="tenant-persisted-1", status="ACTIVE")
        prof_t = TeacherProfile(teacher_id=teacher.id, tenant_id="tenant-persisted-1")
        prof_s = StudentProfile(student_id=student.id)
        session.add_all([mem_admin, prof_t, prof_s])
        await session.commit()
        
        c = Classroom(classroom_key="c-persisted-1", tenant_id="tenant-persisted-1", teacher_profile_id=prof_t.id)
        session.add(c)
        await session.commit()
        
        cm = ClassMembership(classroom_id=c.id, student_id=prof_s.id)
        session.add(cm)
        await session.commit()
        
    # Simulate total server/API shutdown
    await engine1.dispose()
    
    # --- PHASE 2: Reconnect fresh engine (Restart) and verify persisted retrieval ---
    engine2 = create_async_engine(db_url)
    factory2 = async_sessionmaker(engine2, expire_on_commit=False)
    async with factory2() as session:
        retrieved_tenant = await session.scalar(
            select(SchoolTenant).where(SchoolTenant.tenant_id == "tenant-persisted-1")
        )
        assert retrieved_tenant is not None
        assert retrieved_tenant.school_name == "دبیرستان ماندگار"
        
        # Verify 4 roles persisted
        roles = (await session.scalars(select(User.role))).all()
        assert "SCHOOL_ADMIN" in roles
        assert "TEACHER" in roles
        assert "STUDENT" in roles
        
        # Verify memberships and classrooms persisted
        admin_mem = await session.scalar(
            select(SchoolAdminMembership).where(SchoolAdminMembership.tenant_id == "tenant-persisted-1")
        )
        assert admin_mem is not None
        assert admin_mem.status == "ACTIVE"
        
        teacher_prof = await session.scalar(
            select(TeacherProfile).where(TeacherProfile.tenant_id == "tenant-persisted-1")
        )
        assert teacher_prof is not None
        
        classroom = await session.scalar(
            select(Classroom).where(Classroom.classroom_key == "c-persisted-1")
        )
        assert classroom is not None
        assert classroom.teacher_profile_id == teacher_prof.id
        
        membership = await session.scalar(
            select(ClassMembership).where(ClassMembership.classroom_id == classroom.id)
        )
        assert membership is not None
        assert membership.student_id == prof_s.id
        
    await engine2.dispose()
