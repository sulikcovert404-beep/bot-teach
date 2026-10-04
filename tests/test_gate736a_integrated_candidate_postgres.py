"""Integrated Gate736A release-candidate flow on one disposable PostgreSQL DB."""

import asyncio
import os
import secrets
import subprocess
import sys
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient


def test_integrated_candidate_membership_enrollment_submission_and_review(monkeypatch):
    port = os.environ.get("GATE736A_PG_PORT")
    admin_password = os.environ.get("GATE736A_ADMIN_PASSWORD")
    if not port or not admin_password:
        pytest.skip("Explicit isolated Gate736A PostgreSQL disposable required")
    assert port.isdigit() and 1 <= int(port) <= 65535
    runtime_password = secrets.token_urlsafe(32)
    jwt_secret = secrets.token_urlsafe(48)
    database = "gate736a_" + uuid4().hex
    admin_url = f"postgresql+asyncpg://gate736a:{admin_password}@127.0.0.1:{port}/{database}"

    async def connect(dbname: str, user: str = "gate736a", password: str | None = None):
        return await asyncpg.connect(
            host="127.0.0.1", port=int(port), user=user,
            password=password if password is not None else admin_password, database=dbname,
        )

    def alembic(*args: str):
        env = os.environ.copy()
        env["DATABASE_URL"] = admin_url
        return subprocess.run(
            [sys.executable, "-B", "-m", "alembic", *args],
            env=env, capture_output=True, text=True, timeout=180, check=False,
        )

    async def prepare_database():
        admin = await connect("gate736a_test")
        try:
            assert await admin.fetchval("SELECT current_user") == "gate736a"
            assert not await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_runtime')"
            ), "unexpected runtime role in fresh disposable cluster"
            await admin.execute(
                "CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS "
                f"PASSWORD '{runtime_password}'"
            )
            await admin.execute(f'CREATE DATABASE "{database}"')
        finally:
            await admin.close()
        result = await asyncio.to_thread(lambda: alembic("upgrade", "20261003_0026"))
        assert result.returncode == 0, result.stderr

    async def seed_and_check_catalog():
        admin = await connect(database)
        try:
            assert await admin.fetchval("SELECT version_num FROM alembic_version") == "20261003_0026"
            assert await admin.fetchval("SELECT count(*) FROM pg_proc WHERE proname='resolve_tenant'") == 1
            runtime = await admin.fetchrow(
                "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname='app_runtime'"
            )
            assert runtime["rolsuper"] is False and runtime["rolbypassrls"] is False
            assert not await admin.fetchval(
                "SELECT has_table_privilege('app_runtime','public.user_tenant_memberships','INSERT')"
            )
            for table in ("user_tenant_memberships", "class_memberships"):
                for privilege in ("INSERT", "UPDATE", "DELETE"):
                    assert not await admin.fetchval(
                        "SELECT has_table_privilege('app_runtime',$1,$2)",
                        f"public.{table}", privilege,
                    )
            assert await admin.fetchval(
                "SELECT public_execute FROM (SELECT EXISTS (SELECT 1 FROM aclexplode "
                "(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0 "
                "AND a.privilege_type='EXECUTE') AS public_execute FROM pg_proc p "
                "WHERE p.oid='public.enroll_class_student(integer,text,integer,integer)'::regprocedure) q"
            ) is False
            assert await admin.fetchval(
                "SELECT has_function_privilege('app_runtime',"
                "'public.enroll_class_student(integer,text,integer,integer)','EXECUTE')"
            ) is True
            await admin.execute("""
                INSERT INTO public.users(id,role) VALUES
                    (73601,'SUPER_ADMIN'),(73602,'SCHOOL_ADMIN'),(73603,'TEACHER'),
                    (73604,'STUDENT'),(73605,'STUDENT'),(73606,'TEACHER'),
                    (73607,'SCHOOL_ADMIN'),(73608,'STUDENT'),(73609,'SCHOOL_ADMIN'),
                    (73610,'STUDENT'),(73611,'TEACHER');
                INSERT INTO public.school_tenants(tenant_id,school_name)
                    VALUES ('gate736a-a','Gate736A A'),('gate736a-b','Gate736A B');
                INSERT INTO public.user_tenant_memberships(user_id,tenant_id,status)
                    VALUES (73602,'gate736a-a','ACTIVE'),(73603,'gate736a-a','ACTIVE'),
                           (73604,'gate736a-a','ACTIVE'),(73605,'gate736a-b','ACTIVE'),
                           (73606,'gate736a-b','ACTIVE'),(73607,'gate736a-b','ACTIVE');
                INSERT INTO public.teacher_profiles(teacher_id,tenant_id)
                    VALUES (73603,'gate736a-a'),(73606,'gate736a-b');
                INSERT INTO public.student_profiles(student_id) VALUES (73604),(73605),(73608),(73610);
                INSERT INTO public.classrooms(classroom_key,tenant_id,teacher_profile_id)
                    SELECT 'class-'||tp.tenant_id,tp.tenant_id,tp.id FROM public.teacher_profiles tp;
                INSERT INTO public.assignments(teacher_id,classroom_id,tenant_id,title,status,idempotency_key)
                    SELECT tp.teacher_id,c.id,tp.tenant_id,'Gate736A integrated assignment',
                           'PUBLISHED','gate736a-assignment'
                      FROM public.teacher_profiles tp JOIN public.classrooms c
                        ON c.teacher_profile_id=tp.id WHERE tp.tenant_id='gate736a-a';
                INSERT INTO public.assignment_targets(assignment_id,classroom_id,tenant_id)
                    SELECT id,classroom_id,tenant_id FROM public.assignments
                     WHERE idempotency_key='gate736a-assignment';
                INSERT INTO public.assignment_snapshots(assignment_id,tenant_id,version,payload_json,content_digest)
                    SELECT id,tenant_id,1,'{}',repeat('c',64) FROM public.assignments
                     WHERE idempotency_key='gate736a-assignment';
                GRANT USAGE ON SCHEMA public TO app_runtime;
                GRANT SELECT ON public.subscriptions,public.student_profiles,public.assignments,
                    public.assignment_targets,public.assignment_snapshots,public.class_memberships,
                    public.teacher_profiles,public.classrooms TO app_runtime;
                GRANT SELECT,INSERT,UPDATE ON public.student_submissions TO app_runtime;
                GRANT SELECT,INSERT ON public.submission_revisions TO app_runtime;
                GRANT SELECT,INSERT,UPDATE ON public.submission_reviews TO app_runtime;
                GRANT SELECT,INSERT ON public.audit_logs TO app_runtime;
                GRANT USAGE,SELECT ON SEQUENCE public.student_submissions_id_seq,
                    public.submission_revisions_id_seq,public.submission_reviews_id_seq,
                    public.audit_logs_id_seq TO app_runtime;
            """)
            ids = await admin.fetchrow("""
                SELECT (SELECT id FROM classrooms WHERE tenant_id='gate736a-a') AS class_a,
                       (SELECT id FROM classrooms WHERE tenant_id='gate736a-b') AS class_b,
                       (SELECT id FROM assignments WHERE idempotency_key='gate736a-assignment') AS assignment_a,
                       (SELECT id FROM student_profiles WHERE student_id=73604) AS student_profile_a
            """)
        finally:
            await admin.close()
        return ids

    async def exercise_http(ids):
        monkeypatch.setenv(
            "DATABASE_URL",
            f"postgresql+asyncpg://app_runtime:{runtime_password}@127.0.0.1:{port}/{database}",
        )
        monkeypatch.setenv("JWT_SECRET", jwt_secret)
        monkeypatch.setenv("REDIS_URL", "")
        from app.core.config import get_settings
        get_settings.cache_clear()
        from app.main import app
        from app.security.tokens import create_access_token

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            def auth(user_id: int, role: str) -> dict[str, str]:
                token = create_access_token(str(user_id), jwt_secret, role=role)
                return {"Authorization": f"Bearer {token}"}

            # Tenant provisioning and idempotent replay operate on this candidate DB.
            provision_url = "/api/v1/admin/tenants/gate736a-a/memberships"
            provision = {"user_id":73608,"role":"STUDENT","idempotency_key":"gate736a-provision"}
            assert (await client.post(provision_url,json=provision)).status_code == 401
            school_admin = auth(73602,"SCHOOL_ADMIN")
            created = await client.post(provision_url,headers=school_admin,json=provision)
            assert created.status_code == 201 and created.json()["status"] == "CREATED", created.text
            replay = await client.post(provision_url,headers=school_admin,json=provision)
            assert replay.status_code == 201 and replay.json()["status"] == "REPLAY"
            bootstrap_body = {
                "tenant_id":"gate736a-c", "school_name":"Gate736A bootstrap",
                "region":"test", "school_admin_user_id":73609,
                "idempotency_key":"gate736a-bootstrap",
            }
            bootstrap_url = "/api/v1/admin/tenants/bootstrap"
            bootstrap = await client.post(bootstrap_url,headers=auth(73601,"SUPER_ADMIN"),
                                         json=bootstrap_body)
            assert bootstrap.status_code == 201 and bootstrap.json()["status"] == "CREATED"
            bootstrap_replay = await client.post(bootstrap_url,headers=auth(73601,"SUPER_ADMIN"),
                                                 json=bootstrap_body)
            assert bootstrap_replay.status_code == 201 and bootstrap_replay.json()["status"] == "REPLAY"
            assert (await client.post(bootstrap_url,headers=school_admin,
                                      json={**bootstrap_body,"tenant_id":"forged"})).status_code == 403

            async def provision_same_target(key):
                return await client.post(provision_url,headers=school_admin,json={
                    "user_id":73610,"role":"STUDENT","idempotency_key":key,
                })
            same_target = await asyncio.gather(
                provision_same_target("gate736a-same-a"),
                provision_same_target("gate736a-same-b"),
            )
            assert all(response.status_code == 201 for response in same_target)
            assert sorted(response.json()["status"] for response in same_target) == ["CREATED","EXISTING"]

            async def provision_competing_tenant(tenant_id):
                return await client.post(
                    f"/api/v1/admin/tenants/{tenant_id}/memberships",
                    headers=auth(73601,"SUPER_ADMIN"),
                    json={"user_id":73611,"role":"TEACHER",
                          "idempotency_key":f"gate736a-compete-{tenant_id}"},
                )
            competing = await asyncio.gather(
                provision_competing_tenant("gate736a-a"),
                provision_competing_tenant("gate736a-b"),
            )
            assert sorted(response.status_code for response in competing) == [201,409]
            admin = await connect(database)
            try:
                assert await admin.fetchval(
                    "SELECT count(*) FROM public.user_tenant_memberships "
                    "WHERE user_id=73611 AND status='ACTIVE'"
                ) == 1
            finally:
                await admin.close()

            # Class enrollment only after canonical tenant membership exists.
            class_url = f"/api/v1/school-admin/classrooms/{ids['class_a']}/students"
            assert (await client.post(class_url,json={"student_user_id":73608})).status_code == 401
            assert (await client.post(class_url,headers=auth(73603,"TEACHER"),
                                      json={"student_user_id":73608})).status_code == 403
            assert (await client.post(class_url,headers=auth(73604,"STUDENT"),
                                      json={"student_user_id":73608})).status_code == 403
            assert (await client.post(
                f"/api/v1/school-admin/classrooms/{ids['class_b']}/students",
                headers=school_admin,json={"student_user_id":73608},
            )).status_code == 403
            assert (await client.post(class_url,headers=auth(73607,"SCHOOL_ADMIN"),
                                      json={"student_user_id":73608})).status_code == 403
            assert (await client.post(class_url,headers=school_admin,
                                      json={"student_user_id":73605,"tenant_id":"gate736a-a"})).status_code == 403
            student_headers = auth(73608,"STUDENT")
            assignments_url = "/api/v1/student/v1/assignments"
            before = await client.get(assignments_url,headers=student_headers)
            assert before.status_code == 200 and before.json()["assignments"] == []
            async def duplicate_enroll():
                return await client.post(class_url,headers=school_admin,
                                         json={"student_user_id":73608,"tenant_id":"gate736a-b"})
            concurrent = await asyncio.gather(duplicate_enroll(),duplicate_enroll())
            assert all(r.status_code == 201 for r in concurrent)
            assert {r.json()["status"] for r in concurrent} == {"CREATED","EXISTING"}
            visible = await client.get(assignments_url,headers=student_headers)
            assert visible.status_code == 200
            assert [a["id"] for a in visible.json()["assignments"]] == [ids["assignment_a"]]

            # Submission revisions, replay/conflict, and exact-revision review in the same DB.
            submit_url = f"/api/v1/student/v1/assignments/{ids['assignment_a']}/submissions"
            async def submit_same_request():
                return await client.post(submit_url,headers=student_headers,
                                         json={"idempotency_key":"gate736a-submit-1","content":{"answer":1}})
            first_race = await asyncio.gather(submit_same_request(),submit_same_request())
            assert all(response.status_code == 201 for response in first_race)
            assert sorted(response.json()["replayed"] for response in first_race) == [False,True]
            assert len({response.json()["submission_revision_id"] for response in first_race}) == 1
            first = next(response for response in first_race if not response.json()["replayed"])
            submission_id = first.json()["submission_id"]
            revision_id = first.json()["submission_revision_id"]
            conflict = await client.post(submit_url,headers=student_headers,
                                         json={"idempotency_key":"gate736a-submit-1","content":{"answer":2}})
            assert conflict.status_code == 409
            second = await client.post(submit_url,headers=student_headers,
                                       json={"idempotency_key":"gate736a-submit-2","content":{"answer":2}})
            assert second.status_code == 201 and second.json()["revision"] == 2
            async def submit_next_revision(key, answer):
                return await client.post(submit_url,headers=student_headers,
                                         json={"idempotency_key":key,"content":{"answer":answer}})
            sequencing = await asyncio.gather(
                submit_next_revision("gate736a-submit-3",3),
                submit_next_revision("gate736a-submit-4",4),
            )
            assert all(response.status_code == 201 for response in sequencing)
            assert sorted(response.json()["revision"] for response in sequencing) == [3,4]
            latest_revision = next(response for response in sequencing if response.json()["revision"] == 4)

            teacher_headers = auth(73603,"TEACHER")
            listing = await client.get(f"/api/v1/teacher/v1/assignments/{ids['assignment_a']}/submissions",
                                       headers=teacher_headers)
            assert listing.status_code == 200 and len(listing.json()["submissions"]) == 1
            review = await client.post(f"/api/v1/teacher/v1/submissions/{submission_id}/review",
                                       headers=teacher_headers,json={
                                           "submission_revision_id":revision_id,
                                           "review_status":"REVIEWED","score":9,
                                           "feedback":"synthetic Gate736A review",
                                       })
            assert review.status_code == 201 and review.json()["is_current_revision"] is False
            feedback = await client.get(f"/api/v1/student/v1/submissions/{submission_id}/feedback",
                                        headers=student_headers)
            assert feedback.status_code == 200 and len(feedback.json()["revisions"]) == 4
            assert feedback.json()["revisions"][0]["review"]["feedback"] == "synthetic Gate736A review"
            current_review = await client.post(
                f"/api/v1/teacher/v1/submissions/{submission_id}/review",
                headers=teacher_headers,json={
                    "submission_revision_id":latest_revision.json()["submission_revision_id"],
                    "review_status":"REVIEWED","score":10,
                    "feedback":"synthetic current Gate736A review",
                },
            )
            assert current_review.status_code == 201 and current_review.json()["is_current_revision"] is True
            latest_feedback = await client.get(
                f"/api/v1/student/v1/submissions/{submission_id}/feedback",headers=student_headers,
            )
            assert latest_feedback.status_code == 200
            assert latest_feedback.json()["status"] == "REVIEWED"
            assert latest_feedback.json()["revisions"][3]["review"]["feedback"] == "synthetic current Gate736A review"

            removed = await client.delete(f"{class_url}/73608",headers=school_admin)
            assert removed.status_code == 200 and removed.json()["status"] == "REMOVED"
            denied_after_remove = await client.get(assignments_url,headers=student_headers)
            assert denied_after_remove.status_code == 200 and denied_after_remove.json()["assignments"] == []
            admin = await connect(database)
            try:
                assert await admin.fetchval("SELECT public.resolve_tenant(73608)") == "gate736a-a"
                assert await admin.fetchval("SELECT count(*) FROM public.user_tenant_memberships "
                                            "WHERE user_id=73608 AND status='ACTIVE'") == 1
                assert await admin.fetchval("SELECT count(*) FROM public.class_memberships "
                                            "WHERE classroom_id=$1 AND student_id=$2",
                                            ids["class_a"],ids["student_profile_a"]) == 0
                assert await admin.fetchval("SELECT count(*) FROM public.submission_revisions "
                                            "WHERE submission_id=$1",submission_id) == 4
            finally:
                await admin.close()

            # Legacy enrollment writer remains authenticated and fail-closed.
            legacy = await client.post("/api/v1/teacher/v2/classrooms/1/members",
                                      headers=teacher_headers,json={"student_id":73608})
            assert legacy.status_code == 410
            revoked = await client.delete(
                "/api/v1/admin/tenants/gate736a-a/memberships/73608",
                headers={**school_admin,"Idempotency-Key":"gate736a-revoke"},
            )
            assert revoked.status_code == 200 and revoked.json()["status"] == "REVOKED"
            assert (await client.get(assignments_url,headers=student_headers)).status_code == 403

    async def cleanup_database():
        admin = await connect("gate736a_test")
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        finally:
            await admin.close()

    try:
        asyncio.run(prepare_database())
        ids = asyncio.run(seed_and_check_catalog())
        asyncio.run(exercise_http(ids))
        downgrade = asyncio.run(asyncio.to_thread(lambda: alembic("downgrade", "20261003_0025")))
        assert downgrade.returncode == 0, downgrade.stderr
        rebuild = asyncio.run(asyncio.to_thread(lambda: alembic("upgrade", "20261003_0026")))
        assert rebuild.returncode == 0, rebuild.stderr
    finally:
        asyncio.run(cleanup_database())
