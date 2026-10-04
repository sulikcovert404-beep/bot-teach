"""Disposable PostgreSQL qualification for canonical tenant resolution and HTTP."""

import asyncio
import os
import secrets
import subprocess
import sys
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient


def test_canonical_tenant_context_migration_and_http_lifecycle(monkeypatch):
    port = os.environ.get("GATE733_LOCAL_PG_PORT")
    if not port:
        pytest.skip("Explicit Gate733 disposable PostgreSQL port required")
    assert port.isdigit() and 1 <= int(port) <= 65535

    database = "gate733_" + uuid4().hex
    runtime_password = secrets.token_hex(32)
    jwt_secret = secrets.token_hex(32)
    admin_url = f"postgresql+asyncpg://gate732@127.0.0.1:{port}/{database}"

    async def connect(dbname: str, *, user: str = "gate732", password: str | None = None):
        return await asyncpg.connect(
            host="127.0.0.1", port=int(port), user=user, password=password, database=dbname
        )

    def alembic(*args: str):
        environment = os.environ.copy()
        environment["DATABASE_URL"] = admin_url
        return subprocess.run(
            [sys.executable, "-B", "-m", "alembic", *args],
            env=environment, capture_output=True, text=True, timeout=120, check=False,
        )

    async def prepare_database():
        connection = await connect("gate732_test")
        try:
            assert await connection.fetchval("SELECT current_user") == "gate732"
            existing = await connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_runtime')"
            )
            assert not existing, "app_runtime already exists in the disposable cluster; stop without altering it"
            await connection.execute(
                "CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS "
                f"PASSWORD '{runtime_password}'"
            )
            await connection.execute(f'CREATE DATABASE "{database}"')
        finally:
            await connection.close()

    async def qualify_database_and_http():
        connection = await connect(database)
        try:
            assert await connection.fetchval("SELECT current_database()") == database
            assert await connection.fetchval("SELECT current_user") == "gate732"
            assert await connection.fetchval("SELECT version_num FROM alembic_version") == "20261003_0031"

            contract = await connection.fetchrow("""
                SELECT p.prosecdef, p.provolatile, p.proconfig,
                       owner.rolname AS owner,
                       EXISTS (
                           SELECT 1 FROM aclexplode(
                               COALESCE(p.proacl, acldefault('f', p.proowner))
                           ) AS acl
                           WHERE acl.grantee = 0 AND acl.privilege_type = 'EXECUTE'
                       ) AS public_execute,
                       has_function_privilege('app_runtime', p.oid, 'EXECUTE') AS runtime_execute,
                       has_table_privilege('app_runtime', 'public.user_tenant_memberships', 'SELECT') AS membership_select,
                       runtime.rolsuper AS runtime_super,
                       runtime.rolbypassrls AS runtime_bypass
                  FROM pg_proc AS p
                  JOIN pg_roles AS owner ON owner.oid = p.proowner
                  CROSS JOIN pg_roles AS runtime
                 WHERE p.oid = 'public.resolve_tenant(integer)'::regprocedure
                   AND runtime.rolname = 'app_runtime'
            """)
            assert contract["prosecdef"] is True
            assert contract["provolatile"] in ("s", b"s")
            assert contract["owner"] == "gate732"
            assert "search_path=pg_catalog" in contract["proconfig"]
            assert contract["public_execute"] is False
            assert contract["runtime_execute"] is True
            assert contract["membership_select"] is False
            assert contract["runtime_super"] is False
            assert contract["runtime_bypass"] is False
            provisioning_functions = await connection.fetch("""
                SELECT p.proname,p.prosecdef,p.proconfig,
                    owner.rolname AS owner,
                    has_function_privilege('app_runtime',p.oid,'EXECUTE') AS runtime_execute,
                    EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
                            WHERE a.grantee=0 AND a.privilege_type='EXECUTE') AS public_execute
                FROM pg_proc p JOIN pg_roles owner ON owner.oid=p.proowner
                WHERE p.proname IN ('bootstrap_school_tenant','provision_tenant_membership',
                    'revoke_tenant_membership','get_tenant_membership')
            """)
            assert len(provisioning_functions) == 4
            assert all(row["prosecdef"] and row["owner"] == "gate732" for row in provisioning_functions)
            assert all("search_path=pg_catalog" in row["proconfig"] for row in provisioning_functions)
            assert all(row["runtime_execute"] and not row["public_execute"] for row in provisioning_functions)
            assert not await connection.fetchval(
                "SELECT has_table_privilege('app_runtime','public.user_tenant_memberships','INSERT')"
            )

            # Exactly one active row resolves; zero, revoked/suspended, and
            # multiple active rows all return NULL for fail-closed handling.
            await connection.execute("""
                INSERT INTO users(id, role) VALUES
                    (73001,'TEACHER'), (73002,'STUDENT'), (73003,'STUDENT'),
                    (73004,'TEACHER'), (73005,'STUDENT'), (73006,'STUDENT'),
                    (73007,'SUPER_ADMIN'), (73008,'SCHOOL_ADMIN'), (73009,'TEACHER'),
                    (73010,'STUDENT'), (73011,'SCHOOL_ADMIN'), (73012,'TEACHER'),
                    (73013,'SCHOOL_ADMIN');
                INSERT INTO school_tenants(tenant_id, school_name)
                    VALUES ('gate733-a','Gate733 A'), ('gate733-b','Gate733 B');
                INSERT INTO user_tenant_memberships(user_id,tenant_id,status)
                    VALUES (73001,'gate733-a','ACTIVE'), (73002,'gate733-a','ACTIVE'),
                           (73003,'gate733-a','REVOKED'), (73004,'gate733-b','ACTIVE'),
                           (73005,'gate733-b','ACTIVE'), (73006,'gate733-a','ACTIVE'),
                           (73006,'gate733-b','ACTIVE'), (73008,'gate733-a','ACTIVE'),
                           (73013,'gate733-a','ACTIVE');
            """)
            assert await connection.fetchval("SELECT public.resolve_tenant(73001)") == "gate733-a"
            assert await connection.fetchval("SELECT public.resolve_tenant(73003)") is None
            assert await connection.fetchval("SELECT public.resolve_tenant(73999)") is None
            assert await connection.fetchval("SELECT public.resolve_tenant(73006)") is None
            await connection.execute(
                "INSERT INTO user_tenant_memberships(user_id,tenant_id,status) "
                "VALUES (73003,'gate733-b','SUSPENDED')"
            )
            assert await connection.fetchval("SELECT public.resolve_tenant(73003)") is None

            # Build only synthetic data inside this disposable database.
            await connection.execute("""
                INSERT INTO teacher_profiles(teacher_id,tenant_id)
                    VALUES (73001,'gate733-a'), (73004,'gate733-b');
                INSERT INTO student_profiles(student_id) VALUES (73002),(73005);
                INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id)
                    SELECT 'class-' || tp.tenant_id, tp.tenant_id, tp.id FROM teacher_profiles tp
                    WHERE tp.teacher_id IN (73001,73004);
                INSERT INTO class_memberships(classroom_id,student_id)
                    SELECT c.id, sp.id FROM classrooms c
                    JOIN teacher_profiles tp ON tp.id=c.teacher_profile_id
                    JOIN student_profiles sp ON sp.student_id=CASE tp.teacher_id
                        WHEN 73001 THEN 73002 ELSE 73005 END;
                INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status)
                    SELECT tp.teacher_id,c.id,tp.tenant_id,'Gate733 assignment','PUBLISHED'
                    FROM teacher_profiles tp JOIN classrooms c ON c.teacher_profile_id=tp.id;
                INSERT INTO assignment_targets(assignment_id,classroom_id,tenant_id)
                    SELECT id,classroom_id,tenant_id FROM assignments WHERE title='Gate733 assignment';
                INSERT INTO assignment_snapshots(assignment_id,tenant_id,version,payload_json,content_digest)
                    SELECT id,tenant_id,1,'{}',repeat('a',64) FROM assignments WHERE title='Gate733 assignment';
                INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES (73009,'gate733-a');
                INSERT INTO student_profiles(student_id) VALUES (73010);
                INSERT INTO class_memberships(classroom_id,student_id)
                    SELECT c.id,sp.id FROM classrooms c JOIN student_profiles sp ON sp.student_id=73010
                     WHERE c.tenant_id='gate733-a';
            """)
            ids = await connection.fetchrow("""
                SELECT
                    (SELECT id FROM assignments WHERE tenant_id='gate733-a') AS assignment_a,
                    (SELECT id FROM assignments WHERE tenant_id='gate733-b') AS assignment_b,
                    (SELECT id FROM student_profiles WHERE student_id=73002) AS student_a,
                    (SELECT id FROM student_profiles WHERE student_id=73005) AS student_b;
            """)

            # Narrow test-only privileges let HTTP use the real restricted role.
            await connection.execute("GRANT USAGE ON SCHEMA public TO app_runtime")
            await connection.execute("""
                GRANT SELECT ON assignments, assignment_targets, class_memberships,
                    assignment_snapshots, student_profiles, subscriptions, exam_attempts,
                    teacher_profiles, classrooms TO app_runtime;
                GRANT SELECT, INSERT, UPDATE ON student_submissions TO app_runtime;
                GRANT SELECT, INSERT ON submission_revisions TO app_runtime;
                GRANT SELECT, INSERT, UPDATE ON submission_reviews TO app_runtime;
                GRANT SELECT, INSERT ON audit_logs TO app_runtime;
                GRANT USAGE, SELECT ON SEQUENCE student_submissions_id_seq,
                    submission_revisions_id_seq, submission_reviews_id_seq,
                    audit_logs_id_seq TO app_runtime;
            """)
        finally:
            await connection.close()

        # Prove the database boundary also holds for a direct least-privilege
        # runtime connection, with no membership table grant.
        runtime = await connect(database, user="app_runtime", password=runtime_password)
        try:
            assert await runtime.fetchval("SELECT current_user") == "app_runtime"
            assert await runtime.fetchval("SELECT public.resolve_tenant(73001)") == "gate733-a"
            async with runtime.transaction():
                assert await runtime.fetchval("SELECT count(*) FROM assignments") == 0
                await runtime.execute("SELECT set_config('app.tenant_id',$1,true)", "gate733-a")
                assert await runtime.fetchval("SELECT count(*) FROM assignments") == 1
                await runtime.execute("SELECT set_config('app.tenant_id',$1,true)", "gate733-b")
                assert await runtime.fetchval("SELECT count(*) FROM assignments") == 1
        finally:
            await runtime.close()

        monkeypatch.setenv("DATABASE_URL", f"postgresql+asyncpg://app_runtime:{runtime_password}@127.0.0.1:{port}/{database}")
        monkeypatch.setenv("JWT_SECRET", jwt_secret)
        monkeypatch.setenv("REDIS_URL", "")
        from app.core.config import get_settings

        get_settings.cache_clear()
        from app.api.routes.auth import get_session
        from app.main import app
        from app.security.tokens import create_access_token

        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

        def token(user_id: int, role: str) -> str:
            return create_access_token(str(user_id), jwt_secret, role=role)

        def auth(user_id: int, role: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {token(user_id, role)}"}

        # The retired legacy write route must not even resolve the database
        # session dependency; authenticated requests receive an explicit 410.
        session_dependency_calls = 0

        async def unexpected_session_dependency():
            nonlocal session_dependency_calls
            session_dependency_calls += 1
            raise AssertionError("retired legacy membership route resolved a DB session")

        previous_session_override = app.dependency_overrides.get(get_session)
        app.dependency_overrides[get_session] = unexpected_session_dependency
        try:
            legacy_response = await client.post(
                "/api/v1/teacher/v2/classrooms/1/members",
                headers=auth(73001, "TEACHER"), json={"student_id":73002},
            )
        finally:
            if previous_session_override is None:
                app.dependency_overrides.pop(get_session, None)
            else:
                app.dependency_overrides[get_session] = previous_session_override
        assert legacy_response.status_code == 410
        assert session_dependency_calls == 0

        # Authentication and role checks remain outside tenant selection.
        assert (await client.get("/api/v1/student/v1/assignments")).status_code == 401
        assert (await client.get("/api/v1/student/v1/assignments", headers=auth(73001, "TEACHER"))).status_code == 403

        student_headers = auth(73002, "STUDENT")
        listed = await client.get("/api/v1/student/v1/assignments", headers=student_headers)
        assert listed.status_code == 200, listed.text
        assert [row["id"] for row in listed.json()["assignments"]] == [ids["assignment_a"]]
        detail = await client.get(f"/api/v1/student/v1/assignments/{ids['assignment_a']}?tenant_id=gate733-b", headers=student_headers)
        assert detail.status_code == 200, detail.text
        cross_tenant = await client.get(f"/api/v1/student/v1/assignments/{ids['assignment_b']}", headers=student_headers)
        assert cross_tenant.status_code == 404

        submit_url = f"/api/v1/student/v1/assignments/{ids['assignment_a']}/submissions"
        submitted = await client.post(submit_url, headers=student_headers, json={"idempotency_key":"gate733-first","content":{"answer":1}})
        assert submitted.status_code == 201, submitted.text
        submission_id = submitted.json()["submission_id"]
        revision_id = submitted.json()["submission_revision_id"]
        replay = await client.post(submit_url, headers=student_headers, json={"idempotency_key":"gate733-first","content":{"answer":1}})
        assert replay.status_code == 201 and replay.json()["replayed"] is True
        conflict = await client.post(submit_url, headers=student_headers, json={"idempotency_key":"gate733-first","content":{"answer":2}})
        assert conflict.status_code == 409
        next_revision = await client.post(submit_url, headers=student_headers, json={"idempotency_key":"gate733-second","content":{"answer":2}})
        assert next_revision.status_code == 201 and next_revision.json()["revision"] == 2

        teacher_headers = auth(73001, "TEACHER")
        teacher_list = await client.get(f"/api/v1/teacher/v1/assignments/{ids['assignment_a']}/submissions", headers=teacher_headers)
        assert teacher_list.status_code == 200, teacher_list.text
        assert len(teacher_list.json()["submissions"]) == 1
        review = await client.post(
            f"/api/v1/teacher/v1/submissions/{submission_id}/review",
            headers=teacher_headers,
            json={"submission_revision_id":revision_id,"review_status":"REVIEWED","score":9,"feedback":"Gate733 synthetic feedback"},
        )
        assert review.status_code == 201, review.text
        assert review.json()["submission_revision_id"] == revision_id
        assert review.json()["is_current_revision"] is False
        feedback = await client.get(f"/api/v1/student/v1/submissions/{submission_id}/feedback", headers=student_headers)
        assert feedback.status_code == 200, feedback.text
        historical_feedback = feedback.json()
        assert historical_feedback["status"] == "SUBMITTED"
        assert len(historical_feedback["revisions"]) == 2
        assert historical_feedback["revisions"][0]["is_current"] is False
        assert historical_feedback["revisions"][0]["review"]["feedback"] == "Gate733 synthetic feedback"
        assert historical_feedback["revisions"][1]["is_current"] is True
        assert historical_feedback["revisions"][1]["review"] is None
        current_review = await client.post(
            f"/api/v1/teacher/v1/submissions/{submission_id}/review",
            headers=teacher_headers,
            json={
                "submission_revision_id":next_revision.json()["submission_revision_id"],
                "review_status":"REVIEWED", "score":10,
                "feedback":"Gate733 current synthetic feedback",
            },
        )
        assert current_review.status_code == 201, current_review.text
        assert current_review.json()["is_current_revision"] is True
        assert current_review.json()["status"] == "REVIEWED"
        reviewed_feedback = (await client.get(
            f"/api/v1/student/v1/submissions/{submission_id}/feedback",
            headers=student_headers,
        )).json()
        assert reviewed_feedback["status"] == "REVIEWED"
        assert reviewed_feedback["revisions"][0]["review"]["feedback"] == "Gate733 synthetic feedback"
        assert reviewed_feedback["revisions"][1]["review"]["feedback"] == "Gate733 current synthetic feedback"
        assert (await client.get(f"/api/v1/student/v1/submissions/{submission_id}/feedback", headers=auth(73005,"STUDENT"))).status_code == 404
        assert (await client.post(
            f"/api/v1/teacher/v1/submissions/{submission_id}/review",
            headers=auth(73004,"TEACHER"),
            json={"submission_revision_id":revision_id,"review_status":"REVIEWED"},
        )).status_code == 404

        # Membership provisioning is performed through narrow DB-owned
        # functions; the API runtime never receives direct table DML grants.
        assert (await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            json={"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-no-auth"},
        )).status_code == 401
        school_admin_headers = auth(73008, "SCHOOL_ADMIN")
        provision_body = {"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-student-create"}
        created_member = await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=school_admin_headers, json=provision_body,
        )
        assert created_member.status_code == 201, created_member.text
        assert created_member.json()["status"] == "CREATED"
        replay_member = await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=school_admin_headers, json=provision_body,
        )
        assert replay_member.status_code == 201 and replay_member.json()["status"] == "REPLAY"
        existing_member = await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=auth(73007, "SUPER_ADMIN"),
            json={"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-student-existing"},
        )
        assert existing_member.status_code == 201 and existing_member.json()["status"] == "EXISTING"
        async def same_tenant_duplicate():
            return await client.post(
                "/api/v1/admin/tenants/gate733-a/memberships",
                headers=school_admin_headers,
                json={"user_id":73012,"role":"TEACHER","idempotency_key":"gate734-teacher-create"},
            )

        same_tenant_results = await asyncio.gather(
            same_tenant_duplicate(), same_tenant_duplicate(),
        )
        assert sorted(response.status_code for response in same_tenant_results) == [201, 201]
        assert sorted(response.json()["status"] for response in same_tenant_results) == ["CREATED", "REPLAY"]
        membership_check = await connect(database)
        try:
            same_tenant_membership_count = await membership_check.fetchval(
                "SELECT count(*) FROM user_tenant_memberships "
                "WHERE user_id=73012 AND tenant_id='gate733-a' AND status='ACTIVE'"
            )
            assert same_tenant_membership_count == 1
        finally:
            await membership_check.close()
        key_conflict = await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=school_admin_headers,
            json={"user_id":73009,"role":"TEACHER","idempotency_key":"gate734-teacher-create"},
        )
        assert key_conflict.status_code == 409
        student_73010_headers = auth(73010, "STUDENT")
        provisioned_list = await client.get(
            "/api/v1/student/v1/assignments", headers=student_73010_headers,
        )
        assert provisioned_list.status_code == 200 and provisioned_list.json()["assignments"]
        assert (await client.post(
            "/api/v1/admin/tenants/gate733-b/memberships",
            headers=school_admin_headers,
            json={"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-cross-tenant"},
        )).status_code == 403
        assert (await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=auth(73001,"TEACHER"),
            json={"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-teacher-denied"},
        )).status_code == 403
        assert (await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=student_headers,
            json={"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-student-denied"},
        )).status_code == 403
        assert (await client.get(
            "/api/v1/admin/tenants/gate733-b/memberships/73010",
            headers=school_admin_headers,
        )).status_code == 403
        assert (await client.delete(
            "/api/v1/admin/tenants/gate733-a/memberships/73013",
            headers={**school_admin_headers,"Idempotency-Key":"gate734-admin-revoke-denied"},
        )).status_code == 403

        bootstrap_body = {
            "tenant_id":"gate734-new", "school_name":"Gate734 synthetic school",
            "region":"test", "school_admin_user_id":73011,
            "idempotency_key":"gate734-bootstrap",
        }
        bootstrapped = await client.post(
            "/api/v1/admin/tenants/bootstrap", headers=auth(73007,"SUPER_ADMIN"),
            json=bootstrap_body,
        )
        assert bootstrapped.status_code == 201, bootstrapped.text
        assert bootstrapped.json()["status"] == "CREATED"
        bootstrap_replay = await client.post(
            "/api/v1/admin/tenants/bootstrap", headers=auth(73007,"SUPER_ADMIN"),
            json=bootstrap_body,
        )
        assert bootstrap_replay.status_code == 201 and bootstrap_replay.json()["status"] == "REPLAY"
        assert (await client.post(
            "/api/v1/admin/tenants/bootstrap", headers=school_admin_headers,
            json={**bootstrap_body,"tenant_id":"gate734-forbidden","idempotency_key":"gate734-admin-bootstrap"},
        )).status_code == 403

        # The per-user transaction lock serializes competing implicit tenant
        # assignments; exactly one wins and the other deterministically conflicts.
        async def competing(tenant: str):
            return await client.post(
                f"/api/v1/admin/tenants/{tenant}/memberships",
                headers=auth(73007,"SUPER_ADMIN"),
                json={"user_id":73009,"role":"TEACHER","idempotency_key":f"gate734-race-{tenant}"},
            )
        race_results = await asyncio.gather(competing("gate733-a"), competing("gate733-b"))
        assert sorted(response.status_code for response in race_results) == [201,409]
        assert sorted(response.json()["status"] for response in race_results if response.status_code == 201) == ["CREATED"]

        revoked = await client.delete(
            "/api/v1/admin/tenants/gate733-a/memberships/73010",
            headers={**school_admin_headers,"Idempotency-Key":"gate734-student-revoke"},
        )
        assert revoked.status_code == 200 and revoked.json()["status"] == "REVOKED"
        assert (await client.post(
            "/api/v1/admin/tenants/gate733-a/memberships",
            headers=school_admin_headers,
            json={"user_id":73010,"role":"STUDENT","idempotency_key":"gate734-revive-denied"},
        )).status_code == 409
        assert (await client.get(
            "/api/v1/student/v1/assignments", headers=student_73010_headers,
        )).status_code == 403
        membership_read = await client.get(
            "/api/v1/admin/tenants/gate733-a/memberships/73010",
            headers=auth(73007,"SUPER_ADMIN"),
        )
        assert membership_read.status_code == 200 and membership_read.json()["status"] == "REVOKED"
        authority_change = await connect(database)
        try:
            await authority_change.execute("UPDATE users SET role='STUDENT' WHERE id=73007")
        finally:
            await authority_change.close()
        stale_admin_replay = await client.post(
            "/api/v1/admin/tenants/bootstrap", headers=auth(73007,"SUPER_ADMIN"),
            json=bootstrap_body,
        )
        assert stale_admin_replay.status_code == 403
        await client.aclose()

        # Empty downgrade/re-upgrade is qualified above data creation. Once
        # memberships exist, destructive downgrade must be refused atomically.
        assert await asyncio.to_thread(lambda: alembic("downgrade", "20260921_0022").returncode) != 0
        check = await connect(database)
        try:
            assert await check.fetchval("SELECT version_num FROM alembic_version") == "20261003_0031"
            assert await check.fetchval("SELECT count(*) FROM user_tenant_memberships") == 14
            assert await check.fetchval("""
                SELECT count(*) FROM audit_logs
                WHERE action IN ('TENANT_BOOTSTRAPPED','TENANT_MEMBERSHIP_PROVISIONED','TENANT_MEMBERSHIP_REVOKED')
            """) == 5
            assert await check.fetchval("""
                SELECT count(*) FROM audit_logs
                WHERE action IN ('TENANT_BOOTSTRAPPED','TENANT_MEMBERSHIP_PROVISIONED','TENANT_MEMBERSHIP_REVOKED')
                  AND (metadata_json::jsonb ?| ARRAY['token','secret','password','authorization'])
            """) == 0
        finally:
            await check.close()

    async def cleanup():
        connection = await connect("gate732_test")
        try:
            await connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=$1",
                database,
            )
            await connection.execute(f'DROP DATABASE IF EXISTS "{database}"')
            await connection.execute("DROP ROLE IF EXISTS app_runtime")
        finally:
            await connection.close()

    asyncio.run(prepare_database())
    try:
        migrated = alembic("upgrade", "20261003_0031")
        assert migrated.returncode == 0, migrated.stderr
        # Candidate history is forward-only; the missing 0023 is never used.
        # A downgrade request must fail without moving the Alembic head.
        downgraded = alembic("downgrade", "20260921_0022")
        assert downgraded.returncode != 0
        rebuilt = alembic("upgrade", "20261003_0031")
        assert rebuilt.returncode == 0, rebuilt.stderr
        asyncio.run(qualify_database_and_http())
    finally:
        asyncio.run(cleanup())
