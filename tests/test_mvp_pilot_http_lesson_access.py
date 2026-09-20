from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (
    ClassMembership,
    Classroom,
    SchoolTenant,
    StudentProfile,
    TeacherProfile,
    User,
)
from app.main import app
from app.security.tokens import create_access_token


@pytest.mark.asyncio
async def test_pilot_http_assignment_publish_and_student_access(tmp_path: Path, monkeypatch) -> None:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'pilot-http.db'}"
    engine = create_async_engine(db_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        session.add_all([
            SchoolTenant(tenant_id="http-a", school_name="HTTP A"),
            SchoolTenant(tenant_id="http-b", school_name="HTTP B"),
            User(id=201, username="teacher-a", role="TEACHER"),
            User(id=202, username="student-a", role="STUDENT"),
            User(id=203, username="student-b", role="STUDENT"),
            User(id=204, username="teacher-b", role="TEACHER"),
        ])
        await session.flush()
        teacher_a = TeacherProfile(teacher_id=201, tenant_id="http-a")
        teacher_b = TeacherProfile(teacher_id=204, tenant_id="http-b")
        student_a = StudentProfile(student_id=202)
        student_b = StudentProfile(student_id=203)
        session.add_all([teacher_a, teacher_b, student_a, student_b])
        await session.flush()
        class_a = Classroom(classroom_key="http-class-a", tenant_id="http-a", teacher_profile_id=teacher_a.id)
        class_b = Classroom(classroom_key="http-class-b", tenant_id="http-b", teacher_profile_id=teacher_b.id)
        session.add_all([class_a, class_b])
        await session.flush()
        session.add(ClassMembership(classroom_id=class_a.id, student_id=student_a.id))
        await session.commit()
        class_a_id, class_b_id = class_a.id, class_b.id

    async def override_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    teacher_token = create_access_token("201", secret, role="TEACHER")
    student_token = create_access_token("202", secret, role="STUDENT")
    other_student_token = create_access_token("203", secret, role="STUDENT")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create = await client.post("/api/v1/teacher/v1/assignments", headers={"Authorization": f"Bearer {teacher_token}"}, json={"classroom_id": str(class_a_id), "title": "زیست persisted", "instructions": "تمرین"})
            assert create.status_code == 201, create.text
            assignment_id = create.json()["assignment"]["id"]
            publish = await client.post(f"/api/v1/teacher/v1/assignments/{assignment_id}/publish", headers={"Authorization": f"Bearer {teacher_token}"})
            assert publish.status_code == 200, publish.text
            mine = await client.get("/api/v1/student/v1/assignments", headers={"Authorization": f"Bearer {student_token}"})
            assert mine.status_code == 200
            assert [a["id"] for a in mine.json()["assignments"]] == [assignment_id]
            detail = await client.get(f"/api/v1/student/v1/assignments/{assignment_id}", headers={"Authorization": f"Bearer {student_token}"})
            assert detail.status_code == 200
            other = await client.get(f"/api/v1/student/v1/assignments/{assignment_id}", headers={"Authorization": f"Bearer {other_student_token}"})
            assert other.status_code == 404
            cross_class = await client.post("/api/v1/teacher/v1/assignments", headers={"Authorization": f"Bearer {teacher_token}"}, json={"classroom_id": str(class_b_id), "title": "نباید مجاز شود", "instructions": ""})
            assert cross_class.status_code == 404
            unpublished = await client.post("/api/v1/teacher/v1/assignments", headers={"Authorization": f"Bearer {teacher_token}"}, json={"classroom_id": str(class_a_id), "title": "هنوز منتشر نشده", "instructions": ""})
            assert unpublished.status_code == 201
            unpublished_id = unpublished.json()["assignment"]["id"]
            hidden = await client.get(f"/api/v1/student/v1/assignments/{unpublished_id}", headers={"Authorization": f"Bearer {student_token}"})
            assert hidden.status_code == 404
            closed = await client.post(f"/api/v1/teacher/v1/assignments/{assignment_id}/close", headers={"Authorization": f"Bearer {teacher_token}"})
            assert closed.status_code == 200
            revoked = await client.get(f"/api/v1/student/v1/assignments/{assignment_id}", headers={"Authorization": f"Bearer {student_token}"})
            assert revoked.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
