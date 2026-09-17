import asyncio

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
async def test_tenant_concurrency_and_connection_reuse_isolation():
    # SQLite memory engine with thread-safe connection sharing for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    # 1. Seed two distinct tenants (Tenant A: Tehran-Alborz, Tenant B: Tehran-Helli)
    async with session_factory() as session:
        t_a = SchoolTenant(tenant_id="tenant-alborz", school_name="دبیرستان البرز")
        t_b = SchoolTenant(tenant_id="tenant-helli", school_name="دبیرستان علامه حلی")
        session.add_all([t_a, t_b])
        await session.commit()
        
        # Add users for each role in both tenants
        admin_a = User(telegram_user_id=101, username="admin_alborz", role="SCHOOL_ADMIN")
        admin_b = User(telegram_user_id=102, username="admin_helli", role="SCHOOL_ADMIN")
        teacher_a = User(telegram_user_id=201, username="teacher_alborz", role="TEACHER")
        teacher_b = User(telegram_user_id=202, username="teacher_helli", role="TEACHER")
        student_a = User(telegram_user_id=301, username="student_alborz", role="STUDENT")
        student_b = User(telegram_user_id=302, username="student_helli", role="STUDENT")
        super_admin = User(telegram_user_id=999, username="superadmin", role="SUPER_ADMIN")
        session.add_all([admin_a, admin_b, teacher_a, teacher_b, student_a, student_b, super_admin])
        await session.commit()
        
        # Memberships
        mem_admin_a = SchoolAdminMembership(user_id=admin_a.id, tenant_id="tenant-alborz", status="ACTIVE")
        mem_admin_b = SchoolAdminMembership(user_id=admin_b.id, tenant_id="tenant-helli", status="ACTIVE")
        prof_t_a = TeacherProfile(teacher_id=teacher_a.id, tenant_id="tenant-alborz")
        prof_t_b = TeacherProfile(teacher_id=teacher_b.id, tenant_id="tenant-helli")
        prof_s_a = StudentProfile(student_id=student_a.id)
        prof_s_b = StudentProfile(student_id=student_b.id)
        session.add_all([mem_admin_a, mem_admin_b, prof_t_a, prof_t_b, prof_s_a, prof_s_b])
        await session.commit()
        
        # Classrooms
        c_a = Classroom(classroom_key="class-101", tenant_id="tenant-alborz", teacher_profile_id=prof_t_a.id)
        c_b = Classroom(classroom_key="class-201", tenant_id="tenant-helli", teacher_profile_id=prof_t_b.id)
        session.add_all([c_a, c_b])
        await session.commit()
        
        cm_a = ClassMembership(classroom_id=c_a.id, student_id=prof_s_a.id)
        cm_b = ClassMembership(classroom_id=c_b.id, student_id=prof_s_b.id)
        session.add_all([cm_a, cm_b])
        await session.commit()
        
    # 2. Concurrency Test: simultaneous access for Tenant A and Tenant B
    async def tenant_admin_query(target_tenant: str, expected_user_id: int):
        async with session_factory() as session:
            res = await session.scalars(
                select(SchoolAdminMembership)
                .where(
                    SchoolAdminMembership.tenant_id == target_tenant,
                    SchoolAdminMembership.status == "ACTIVE"
                )
            )
            admins = res.all()
            assert len(admins) == 1
            assert admins[0].user_id == expected_user_id
            return admins[0].user_id

    results = await asyncio.gather(
        tenant_admin_query("tenant-alborz", admin_a.id),
        tenant_admin_query("tenant-helli", admin_b.id),
        tenant_admin_query("tenant-alborz", admin_a.id),
        tenant_admin_query("tenant-helli", admin_b.id)
    )
    assert results == [admin_a.id, admin_b.id, admin_a.id, admin_b.id]
    
    # 3. Connection Reuse / Pooling Isolation Test:
    async with session_factory() as s1:
        async with s1.begin():
            s1_teachers = (await s1.scalars(
                select(TeacherProfile).where(TeacherProfile.tenant_id == "tenant-alborz")
            )).all()
            assert len(s1_teachers) == 1
            assert s1_teachers[0].teacher_id == teacher_a.id
            
    async with session_factory() as s2:
        async with s2.begin():
            s2_teachers = (await s2.scalars(
                select(TeacherProfile).where(TeacherProfile.tenant_id == "tenant-helli")
            )).all()
            assert len(s2_teachers) == 1
            assert s2_teachers[0].teacher_id == teacher_b.id

    # 4. Cross-Tenant Access DENY & Revoked Membership Deny Test
    async with session_factory() as session:
        # Cross-tenant check: Admin A cannot see Tenant B
        cross_res = (await session.scalars(
            select(SchoolAdminMembership).where(
                SchoolAdminMembership.user_id == admin_a.id,
                SchoolAdminMembership.tenant_id == "tenant-helli"
            )
        )).all()
        assert len(cross_res) == 0  # DENY

        # Revoke Admin A
        admin_mem = await session.scalar(
            select(SchoolAdminMembership).where(
                SchoolAdminMembership.user_id == admin_a.id,
                SchoolAdminMembership.tenant_id == "tenant-alborz"
            )
        )
        admin_mem.status = "REVOKED"
        await session.commit()
        
        # Verify access DENIED when revoked
        active_admins = (await session.scalars(
            select(SchoolAdminMembership).where(
                SchoolAdminMembership.tenant_id == "tenant-alborz",
                SchoolAdminMembership.status == "ACTIVE"
            )
        )).all()
        assert len(active_admins) == 0

    await engine.dispose()
