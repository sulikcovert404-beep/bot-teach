"""PostgreSQL and ASGI qualification for Gate735B; requires a dedicated disposable DB."""

import asyncio
import os
import secrets
import subprocess
import sys
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient


def test_gate735b_class_enrollment_postgres_http_and_privileges(monkeypatch):
    port = os.environ.get("GATE735B_PG_PORT")
    if not port or not os.environ.get("GATE735B_ADMIN_PASSWORD"):
        pytest.skip("Explicit Gate735B disposable PostgreSQL container required")
    assert port.isdigit() and 1 <= int(port) <= 65535
    admin_password = os.environ["GATE735B_ADMIN_PASSWORD"]
    runtime_password = secrets.token_urlsafe(32)
    jwt_secret = secrets.token_urlsafe(48)
    database = "gate735b_" + uuid4().hex
    admin_url = f"postgresql+asyncpg://gate735b:{admin_password}@127.0.0.1:{port}/{database}"

    async def connect(dbname: str, user: str = "gate735b", password: str | None = None):
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

    async def provision_database():
        admin = await connect("postgres")
        try:
            assert await admin.fetchval("SELECT current_user") == "gate735b"
            role_exists = await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_runtime')"
            )
            assert not role_exists, "unexpected app_runtime role in disposable container"
            await admin.execute(
                "CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS "
                f"PASSWORD '{runtime_password}'"
            )
            await admin.execute(f'CREATE DATABASE "{database}"')
        finally:
            await admin.close()
        # Gate735B qualifies the schema contract introduced in 0026; it later
        # exercises the full forward-only candidate chain after its downgrade probe.
        migrated = await asyncio.to_thread(lambda: alembic("upgrade", "20261003_0026"))
        assert migrated.returncode == 0, migrated.stderr

    async def qualify_contract_and_seed():
        admin = await connect(database)
        try:
            assert await admin.fetchval("SELECT version_num FROM alembic_version") == "20261003_0026"
            functions = await admin.fetch("""
                SELECT p.proname,p.prosecdef,p.proconfig,owner.rolname AS owner,
                    has_function_privilege('app_runtime',p.oid,'EXECUTE') AS runtime_execute,
                    EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
                            WHERE a.grantee=0 AND a.privilege_type='EXECUTE') AS public_execute
                FROM pg_proc p JOIN pg_roles owner ON owner.oid=p.proowner
                WHERE p.oid IN (
                    'public.enroll_class_student(integer,text,integer,integer)'::regprocedure,
                    'public.remove_class_student(integer,text,integer,integer)'::regprocedure)
            """)
            assert len(functions) == 2
            assert all(row["prosecdef"] and row["owner"] == "gate735b" for row in functions)
            assert all("search_path=pg_catalog" in row["proconfig"] for row in functions)
            assert all(row["runtime_execute"] and not row["public_execute"] for row in functions)
            assert not await admin.fetchval(
                "SELECT has_table_privilege('app_runtime','public.class_memberships','INSERT')"
            )
            assert not await admin.fetchval(
                "SELECT has_table_privilege('app_runtime','public.class_memberships','DELETE')"
            )
            role = await admin.fetchrow("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname='app_runtime'")
            assert role["rolsuper"] is False and role["rolbypassrls"] is False

            await admin.execute("""
                INSERT INTO public.users(id,role) VALUES
                    (73501,'SCHOOL_ADMIN'),(73502,'STUDENT'),(73503,'STUDENT'),
                    (73504,'TEACHER'),(73505,'SCHOOL_ADMIN'),(73506,'STUDENT');
                INSERT INTO public.school_tenants(tenant_id,school_name)
                    VALUES ('gate735b-a','Gate735B A'),('gate735b-b','Gate735B B');
                INSERT INTO public.user_tenant_memberships(user_id,tenant_id,status)
                    VALUES (73501,'gate735b-a','ACTIVE'),(73502,'gate735b-a','ACTIVE'),
                           (73503,'gate735b-b','ACTIVE'),(73504,'gate735b-a','ACTIVE'),
                           (73505,'gate735b-b','ACTIVE');
                INSERT INTO public.teacher_profiles(teacher_id,tenant_id) VALUES
                    (73504,'gate735b-a'),(73504,'gate735b-b');
                INSERT INTO public.student_profiles(student_id) VALUES (73502),(73503),(73506);
                INSERT INTO public.classrooms(classroom_key,tenant_id,teacher_profile_id)
                    SELECT 'class-'||t.tenant_id,t.tenant_id,tp.id
                    FROM public.teacher_profiles tp JOIN public.school_tenants t ON t.tenant_id=tp.tenant_id;
                INSERT INTO public.assignments(tenant_id,teacher_id,classroom_id,title,status,idempotency_key)
                    SELECT 'gate735b-a',73504,c.id,'Gate735B class access','PUBLISHED','gate735b-assignment'
                    FROM public.classrooms c WHERE c.tenant_id='gate735b-a';
                INSERT INTO public.assignment_targets(assignment_id,classroom_id,tenant_id)
                    SELECT id,classroom_id,tenant_id FROM public.assignments
                    WHERE idempotency_key='gate735b-assignment';
                INSERT INTO public.assignment_snapshots(assignment_id,tenant_id,version,payload_json,content_digest)
                    SELECT id,tenant_id,1,'{}',repeat('b',64) FROM public.assignments
                    WHERE idempotency_key='gate735b-assignment';
                GRANT USAGE ON SCHEMA public TO app_runtime;
                GRANT SELECT ON public.subscriptions,public.student_profiles,public.assignments,
                    public.assignment_targets,public.assignment_snapshots,public.class_memberships TO app_runtime;
            """)
            classroom_ids = await admin.fetchrow("""
                SELECT (SELECT id FROM public.classrooms WHERE tenant_id='gate735b-a') AS local_class,
                       (SELECT id FROM public.classrooms WHERE tenant_id='gate735b-b') AS foreign_class
            """)
        finally:
            await admin.close()
        return classroom_ids

    async def qualify_runtime_and_http(classrooms):
        runtime = await connect(database, "app_runtime", runtime_password)
        try:
            assert await runtime.fetchval("SELECT current_user") == "app_runtime"
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await runtime.execute(
                    "INSERT INTO public.class_memberships(classroom_id,student_id) VALUES ($1,1)",
                    classrooms["local_class"],
                )
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await runtime.execute("DELETE FROM public.class_memberships")
            with pytest.raises(asyncpg.PostgresError, match="class_enrollment_denied"):
                await runtime.fetchval(
                    "SELECT public.enroll_class_student(73504,'TEACHER',$1,73502)",
                    classrooms["local_class"],
                )
            with pytest.raises(asyncpg.PostgresError, match="class_enrollment_denied"):
                await runtime.fetchval(
                    "SELECT public.remove_class_student(73501,'TEACHER',$1,73502)",
                    classrooms["local_class"],
                )
            assert await runtime.fetchval(
                "SELECT public.resolve_tenant(73502)"
            ) == "gate735b-a"
        finally:
            await runtime.close()

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

        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

        def auth(user_id: int, role: str) -> dict[str, str]:
            token = create_access_token(str(user_id), jwt_secret, role=role)
            return {"Authorization": f"Bearer {token}"}

        base = f"/api/v1/school-admin/classrooms/{classrooms['local_class']}/students"
        assert (await client.post(base, json={"student_user_id": 73502})).status_code == 401
        assert (await client.post(base, headers=auth(73504, "TEACHER"),
                                  json={"student_user_id": 73502})).status_code == 403
        assert (await client.post(base, headers=auth(73502, "STUDENT"),
                                  json={"student_user_id": 73502})).status_code == 403
        assert (await client.post(base, headers=auth(73999, "SCHOOL_ADMIN"),
                                  json={"student_user_id": 73502})).status_code == 403
        denied = await client.post(
            f"/api/v1/school-admin/classrooms/{classrooms['foreign_class']}/students",
            headers=auth(73501, "SCHOOL_ADMIN"), json={"student_user_id": 73502},
        )
        assert denied.status_code == 403
        invalid_student = await client.post(
            base, headers=auth(73501, "SCHOOL_ADMIN"), json={"student_user_id": 73506},
        )
        assert invalid_student.status_code == 403
        assert (await client.post(
            base, headers=auth(73505, "SCHOOL_ADMIN"), json={"student_user_id": 73502},
        )).status_code == 403

        # An extra client tenant field is ignored and cannot confer authority.
        body = {"student_user_id": 73502, "tenant_id": "gate735b-b"}
        async def duplicate():
            return await client.post(base, headers=auth(73501, "SCHOOL_ADMIN"), json=body)

        concurrent = await asyncio.gather(duplicate(), duplicate())
        assert all(response.status_code == 201 for response in concurrent)
        assert {response.json()["status"] for response in concurrent} == {"CREATED", "EXISTING"}
        replay = await client.post(base, headers=auth(73501, "SCHOOL_ADMIN"), json=body)
        assert replay.status_code == 201 and replay.json()["status"] == "EXISTING"
        student_auth = auth(73502, "STUDENT")
        access_before = await client.get("/api/v1/student/v1/assignments", headers=student_auth)
        assert access_before.status_code == 200
        assert len(access_before.json()["assignments"]) == 1
        verifier = await connect(database)
        try:
            assert await verifier.fetchval("SELECT count(*) FROM public.class_memberships") == 1
            assert await verifier.fetchval("SELECT count(*) FROM public.audit_logs WHERE action='class_member_added'") == 1
        finally:
            await verifier.close()

        removed = await client.delete(
            f"{base}/73502", headers=auth(73501, "SCHOOL_ADMIN"),
        )
        assert removed.status_code == 200 and removed.json()["status"] == "REMOVED"
        again = await client.delete(f"{base}/73502", headers=auth(73501, "SCHOOL_ADMIN"))
        assert again.status_code == 200 and again.json()["status"] == "ALREADY_ABSENT"
        access_after = await client.get("/api/v1/student/v1/assignments", headers=student_auth)
        assert access_after.status_code == 200
        assert access_after.json()["assignments"] == []
        verifier = await connect(database)
        try:
            assert await verifier.fetchval("SELECT count(*) FROM public.class_memberships") == 0
            assert await verifier.fetchval("""
                SELECT count(*) FROM public.user_tenant_memberships
                 WHERE user_id=73502 AND tenant_id='gate735b-a' AND status='ACTIVE' AND revoked_at IS NULL
            """) == 1
            assert await verifier.fetchval("SELECT public.resolve_tenant(73502)") == "gate735b-a"
            assert await verifier.fetchval("SELECT count(*) FROM public.audit_logs WHERE action='class_member_removed'") == 1
        finally:
            await verifier.close()

        # The retired teacher writer remains a no-DB 410 boundary.
        legacy = await client.post(
            "/api/v1/teacher/v2/classrooms/1/members",
            headers=auth(73504, "TEACHER"), json={"student_id": 73502},
        )
        assert legacy.status_code == 410
        verifier = await connect(database)
        try:
            assert await verifier.fetchval("SELECT count(*) FROM public.class_memberships") == 0
        finally:
            await verifier.close()
        await client.aclose()

    async def cleanup_database():
        admin = await connect("postgres")
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        finally:
            await admin.close()

    try:
        asyncio.run(provision_database())
        classrooms = asyncio.run(qualify_contract_and_seed())
        asyncio.run(qualify_runtime_and_http(classrooms))
        downgraded = asyncio.to_thread
        # Function-only downgrade must be reversible on the disposable database.
        result = asyncio.run(downgraded(lambda: alembic("downgrade", "20261003_0025")))
        assert result.returncode == 0, result.stderr
        rebuilt = asyncio.run(downgraded(lambda: alembic("upgrade", "20261003_0026")))
        assert rebuilt.returncode == 0, rebuilt.stderr
    finally:
        asyncio.run(cleanup_database())
