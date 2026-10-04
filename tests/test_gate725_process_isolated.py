import json
import subprocess
import sys
import textwrap
from pathlib import Path


def test_gate725_process_isolated_vertical_journey(tmp_path: Path) -> None:
    db_path = tmp_path / "gate725-e2e.db"
    child = textwrap.dedent(
        r'''
        import asyncio, json, sys
        from types import SimpleNamespace
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.db.base import Base
        from app.db.models import (SchoolTenant, User, StudentProfile, TeacherProfile,
            Classroom, ClassMembership, Assignment, AssignmentTarget, AssignmentSnapshot,
            UserTenantMembership)
        from app.api.routes.student import (AssignmentSubmissionV1Request, get_student_progress,
            list_assignments_v1, get_assignment_v1, submit_assignment_v1)
        import app.api.routes.tutor as tutor_route
        from app.api.routes.tutor import TutorRequest, tutor_answer
        from app.core.config import get_settings
        from app.api.routes.auth import get_session
        from app.main import app
        from app.security.tenant_context import TenantContext
        import app.security.tenant_context as tenant_context_module
        from app.security.tokens import create_access_token
        from httpx import ASGITransport, AsyncClient

        class FakeTutor:
            def __init__(self, *_args, **_kwargs): pass
            async def answer(self, _query, max_tokens=1200):
                return SimpleNamespace(text="grounded", model="fake", usage_tokens=4,
                    citations=[SimpleNamespace(source_id="book-1", chunk_id="chunk-1", page=2, chapter="1", lesson="1")])

        async def main(path):
            engine = create_async_engine("sqlite+aiosqlite:///" + path)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
            get_settings().gemini_api_key = "test-key"
            get_settings().jwt_secret = "p" * 32
            tutor_route.AITutor = FakeTutor
            async def override_session():
                async with sessions() as request_session: yield request_session
            app.dependency_overrides[get_session] = override_session
            async def sqlite_tenant_context(session, *, user_id):
                return TenantContext(user_id=user_id, tenant_id="p-school")
            tenant_context_module.establish_tenant_context = sqlite_tenant_context
            async with sessions() as s:
                s.add_all([SchoolTenant(tenant_id="p-school", school_name="P"), User(id=1, username="t", role="TEACHER"), User(id=2, username="s", role="STUDENT"), StudentProfile(student_id=2), UserTenantMembership(user_id=2, tenant_id="p-school", status="ACTIVE")])
                await s.flush(); tp=TeacherProfile(teacher_id=1, tenant_id="p-school"); s.add(tp); await s.flush()
                cl=Classroom(classroom_key="p-class", tenant_id="p-school", teacher_profile_id=tp.id); s.add(cl); await s.flush()
                sp=await s.get(StudentProfile, 1); s.add(ClassMembership(classroom_id=cl.id, student_id=sp.id))
                a=Assignment(tenant_id="p-school", teacher_id=1, classroom_id=cl.id, title="p", instructions="", status="PUBLISHED"); s.add(a); await s.flush()
                s.add(AssignmentTarget(assignment_id=a.id, classroom_id=cl.id, tenant_id="p-school")); s.add(AssignmentSnapshot(assignment_id=a.id, tenant_id="p-school", version=1, payload_json="{}", content_digest="d"*64)); await s.commit(); aid=a.id
                token=create_access_token("2", "p" * 32, role="STUDENT")
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    listed_response=await client.get("/api/v1/student/v1/assignments", headers={"Authorization":f"Bearer {token}"})
                assert listed_response.status_code==200 and listed_response.json()["assignments"][0]["id"]==aid
                tenant=TenantContext(user_id=2, tenant_id="p-school")
                listed=await list_assignments_v1(tenant=tenant, _entitled="2", session=s); assert listed["assignments"][0]["id"]==aid
                detail=await get_assignment_v1(aid, tenant=tenant, _entitled="2", session=s); assert detail["assignment"]["id"]==aid
                sub=await submit_assignment_v1(aid, AssignmentSubmissionV1Request(idempotency_key="gate725-submit", content={"answer":"ok"}), tenant=tenant, _entitled="2", session=s); assert sub["revision"]==1
                progress_before=await get_student_progress(subject="2", session=s); assert progress_before["progress_provenance"]["submission_count"]==1
                tutor=await tutor_answer(TutorRequest(query="explain", school_id="p-school", classroom_id=cl.id, assignment_id=aid), subject="2", session=s); assert tutor.citations[0]["source_id"]=="book-1"
                progress_after=await get_student_progress(subject="2", session=s); assert progress_after["progress_provenance"]["tutor_interaction_count"]==1
            app.dependency_overrides.pop(get_session, None)
            await engine.dispose(); print(json.dumps({"status":"PASS","assignment_id":aid,"asgi_list":"PASS"}))
        asyncio.run(main(sys.argv[1]))
        '''
    )
    result = subprocess.run(
        [sys.executable, "-c", child, str(db_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "PASS"
