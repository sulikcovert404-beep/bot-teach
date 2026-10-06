"""A10 disposable PostgreSQL 16 integration qualification (explicit opt-in)."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("GATE_MAOS_A10_ADMIN_DSN", "postgresql://postgres@127.0.0.1:18577/postgres")
PG_CONTAINER = os.environ.get("GATE_MAOS_A10_PG_CONTAINER", "maos-a10-pg16-qualification")
DB_HOST = os.environ.get("GATE_MAOS_A10_DB_HOST", "127.0.0.1")


def test_a10_is_one_explicit_successor_and_forward_only() -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    scripts = ScriptDirectory.from_config(cfg)
    rev = scripts.get_revision("20261006_0034")
    assert rev is not None and rev.down_revision == "20261004_0033"
    src = (ROOT / "migrations/versions/20261006_0034_maos_durable_foundation.py").read_text()
    assert "NOBYPASSRLS" in src and "ON DELETE CASCADE" not in src.upper()
    assert "upgrade head" not in src.lower() and "alembic stamp" not in src.lower()
    assert "provider_idempotency_key" in src and "CRITICAL" in src
    grant = 'GRANT EXECUTE ON FUNCTION public.gate738k_guard_writer() TO maos_audit_owner'
    revoke = 'REVOKE EXECUTE ON FUNCTION public.gate738k_guard_writer() FROM maos_audit_owner'
    assert src.index(grant) < src.index('SET LOCAL ROLE maos_audit_owner')
    assert src.index('RESET ROLE') < src.index(revoke) < src.index('REVOKE maos_audit_owner FROM CURRENT_USER')
    assert 'gate738k_guard_writer() FROM PUBLIC' not in src
    assert 'gate738k_guard_writer() TO app_runtime' not in src


def _assert_dedicated_pg16_target() -> None:
    if os.environ.get("GATE_MAOS_A10_DISPOSABLE") != "1":
        pytest.skip("explicit opt-in required for disposable MAOS A10 PostgreSQL")
    parsed = urlparse(ADMIN_DSN)
    allowed_hosts = {"127.0.0.1", "localhost"}
    if inspected := os.environ.get("GATE_MAOS_A10_PG_INSPECT_JSON"):
        allowed_hosts.add("host.docker.internal")
    if parsed.hostname not in allowed_hosts or parsed.port is None or parsed.path != "/postgres":
        pytest.fail("A10 test accepts only an explicit local or inspected Docker-host PostgreSQL target")
    if DB_HOST != parsed.hostname:
        pytest.fail("A10 test database host does not match the preflighted DSN")
    if PG_CONTAINER != "maos-a10-pg16-qualification" and not PG_CONTAINER.startswith("maos-a10q-"):
        pytest.fail("A10 test accepts only its pinned test container or an A10Q-namespaced disposable")
    inspected = os.environ.get("GATE_MAOS_A10_PG_INSPECT_JSON")
    if inspected:
        try:
            records = json.loads(inspected)
        except json.JSONDecodeError:
            pytest.fail("preflighted PostgreSQL container metadata is not valid JSON")
        if not isinstance(records, list) or len(records) != 1:
            pytest.fail("preflighted PostgreSQL container metadata is ambiguous")
        info = records[0]
    else:
        result = subprocess.run(["docker", "inspect", PG_CONTAINER], check=False,
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            pytest.fail("dedicated disposable PostgreSQL container is unavailable")
        info = json.loads(result.stdout)[0]
    if info.get("Name") != f"/{PG_CONTAINER}":
        pytest.fail("preflighted PostgreSQL container name did not match the explicit target")
    bindings = info.get("NetworkSettings", {}).get("Ports", {}).get("5432/tcp") or []
    if (not info.get("State", {}).get("Running")
            or info.get("Config", {}).get("Image") not in {"postgres:16", "pgvector/pgvector:pg16"}
            or not any(x.get("HostIp") == "127.0.0.1" and x.get("HostPort") == str(parsed.port) for x in bindings)):
        pytest.fail("PostgreSQL target did not match the pinned disposable PG16 container")


def _dsn(db: str, user: str, password: str | None = None) -> str:
    auth = user if password is None else f"{user}:{password}"
    return f"postgresql://{auth}@{DB_HOST}:{urlparse(ADMIN_DSN).port}/{db}"


def _admin_db_dsn(db: str) -> str:
    parsed = urlparse(ADMIN_DSN)
    return _dsn(db, parsed.username or "postgres", parsed.password)


async def _create_test_db(db: str, role: str, password: str) -> None:
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        if not await admin.fetchval("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime'"):
            pytest.fail("app_runtime must be provisioned in the dedicated disposable cluster")
        await admin.execute(f"CREATE ROLE {role} LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '{password}'")
        await admin.execute(f"GRANT app_runtime TO {role}")
        await admin.execute(f"CREATE DATABASE {db}")
    finally:
        await admin.close()

    conn = await asyncpg.connect(_admin_db_dsn(db))
    try:
        await conn.execute("""
            CREATE TABLE public.users(id integer PRIMARY KEY);
            CREATE TABLE public.school_tenants(tenant_id varchar(64) PRIMARY KEY);
            CREATE TABLE public.user_tenant_memberships(user_id integer, tenant_id varchar(64), status varchar(20), revoked_at timestamptz);
            CREATE FUNCTION public.resolve_tenant(p_user_id integer) RETURNS text LANGUAGE sql STABLE
              SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT CASE WHEN count(*)=1 THEN min(tenant_id) END
                FROM public.user_tenant_memberships WHERE user_id=p_user_id AND status='ACTIVE' AND revoked_at IS NULL $$;
            REVOKE ALL ON FUNCTION public.resolve_tenant(integer) FROM PUBLIC;
            GRANT EXECUTE ON FUNCTION public.resolve_tenant(integer) TO app_runtime;
            CREATE TABLE public.ai_teacher_writer_generation_state(generation varchar(40) PRIMARY KEY, database_role varchar(63) UNIQUE, state varchar(16));
            INSERT INTO public.ai_teacher_writer_generation_state VALUES ('legacy','app_runtime','FENCED');
            CREATE FUNCTION public.gate738k_guard_writer() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $g$
              BEGIN IF NOT EXISTS (SELECT 1 FROM public.ai_teacher_writer_generation_state WHERE database_role=session_user AND state='SERVING')
                THEN RAISE EXCEPTION 'writer denied' USING ERRCODE='42501'; END IF;
                IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW; END $g$;
            REVOKE ALL ON FUNCTION public.gate738k_guard_writer() FROM PUBLIC;
            CREATE TABLE public.alembic_version(version_num varchar(32) NOT NULL);
            INSERT INTO public.alembic_version VALUES ('20261004_0033');
            INSERT INTO public.users VALUES (101),(202);
            INSERT INTO public.school_tenants VALUES ('tenant-a'),('tenant-b');
            INSERT INTO public.user_tenant_memberships VALUES (101,'tenant-a','ACTIVE',NULL),(202,'tenant-b','ACTIVE',NULL);
        """)
        await conn.execute(f"INSERT INTO public.ai_teacher_writer_generation_state VALUES ('a10-test','{role}','SERVING')")
    finally:
        await conn.close()

    env = os.environ.copy()
    migration_dsn = _admin_db_dsn(db).replace("postgresql://", "postgresql+asyncpg://", 1)
    env["DATABASE_URL"] = migration_dsn
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-B", "-m", "alembic", "upgrade", "20261006_0034",
        cwd=str(ROOT), env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=90)
    except TimeoutError:
        process.kill()
        await process.communicate()
        raise
    if process.returncode:
        pytest.fail("explicit target 20261006_0034 failed: " + stderr.decode(errors="replace")[-2500:])


async def _drop_test_db(db: str, role: str) -> None:
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await admin.execute("SELECT pg_catalog.pg_terminate_backend(pid) FROM pg_catalog.pg_stat_activity WHERE datname=$1", db)
        await admin.execute(f"DROP DATABASE IF EXISTS {db}")
        await admin.execute(f"DROP ROLE IF EXISTS {role}")
    finally:
        await admin.close()


@pytest.mark.asyncio
async def test_pg16_reservation_rls_audit_and_effect_state_contract() -> None:
    _assert_dedicated_pg16_target()
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        assert int(await admin.fetchval("SHOW server_version_num")) >= 160000
    finally:
        await admin.close()

    suffix = uuid.uuid4().hex[:12]
    db = f"maos_a10_{suffix}"
    role = f"maos_a10_{suffix}"
    password = uuid.uuid4().hex
    try:
        await _create_test_db(db, role, password)
        catalog = await asyncpg.connect(_admin_db_dsn(db))
        try:
            acl = await catalog.fetchrow("""
                SELECT p.oid::regprocedure::text AS identity,
                       pg_catalog.pg_get_userbyid(p.proowner) AS function_owner,
                       pg_catalog.has_function_privilege('app_runtime',p.oid,'EXECUTE') AS runtime_execute,
                       pg_catalog.has_function_privilege('maos_audit_owner',p.oid,'EXECUTE') AS audit_owner_execute,
                       EXISTS (
                           SELECT 1 FROM pg_catalog.aclexplode(
                               COALESCE(p.proacl, pg_catalog.acldefault('f',p.proowner))
                           ) AS acl
                           WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
                       ) AS public_execute,
                       (SELECT count(*) FROM pg_catalog.pg_trigger t
                          JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
                          JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                         WHERE n.nspname='maos' AND NOT t.tgisinternal
                           AND t.tgfoid=p.oid) AS trigger_count
                  FROM pg_catalog.pg_proc p
                  JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
                 WHERE n.nspname='public' AND p.proname='gate738k_guard_writer'
            """)
            assert acl is not None
            assert acl['identity'] == 'gate738k_guard_writer()'
            assert acl['function_owner'] == (urlparse(ADMIN_DSN).username or 'postgres')
            assert acl['runtime_execute'] is False
            assert acl['audit_owner_execute'] is False
            assert acl['public_execute'] is False
            assert acl['trigger_count'] == 6
        finally:
            await catalog.close()
        runtime = await asyncpg.connect(_dsn(db, role, password))
        try:
            operation = uuid.uuid4()
            async with runtime.transaction():
                assert await runtime.fetchval("SELECT maos.set_principal_context(101)") == "tenant-a"
                assert await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'CREATE_ITEM',101)", operation, "a" * 64)
                assert not await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'CREATE_ITEM',101)", operation, "a" * 64)
                with pytest.raises(asyncpg.UniqueViolationError):
                    async with runtime.transaction():
                        await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'CREATE_ITEM',101)", operation, "b" * 64)
                await runtime.fetchval("SELECT maos.set_principal_context(202)")
                assert await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'CREATE_ITEM',202)", operation, "a" * 64)

            rollback_id = uuid.uuid4()
            with pytest.raises(RuntimeError, match="intentional rollback"):
                async with runtime.transaction():
                    await runtime.fetchval("SELECT maos.set_principal_context(101)")
                    assert await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'ROLLBACK_CHECK',101)", rollback_id, "c" * 64)
                    raise RuntimeError("intentional rollback")
            async with runtime.transaction():
                await runtime.fetchval("SELECT maos.set_principal_context(101)")
                assert await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'ROLLBACK_CHECK',101)", rollback_id, "c" * 64)

            op_id, audit_id, intent_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            async with runtime.transaction():
                await runtime.fetchval("SELECT maos.set_principal_context(101)")
                assert await runtime.fetchval("SELECT maos.reserve_operation($1,$2,'SEND_NOTICE',101)", op_id, "d" * 64)
                assert await runtime.fetchval("SELECT maos.append_audit_event($1,'OPERATION_RESERVED','operation',$2,$3,$4)",
                                              audit_id, str(op_id), "e" * 64, uuid.uuid4()) == 1
                assert await runtime.fetchval("SELECT maos.prepare_effect($1,$2,$3,'SEND_NOTICE','HIGH','STUB',$4,$5)",
                                              intent_id, op_id, audit_id, "f" * 64, "1" * 64) == intent_id
                assert await runtime.fetchval("SELECT maos.record_effect_outcome($1,'DISPATCHING','DISPATCH_MARKED',$2)", intent_id, "2" * 64) == 2
                assert await runtime.fetchval("SELECT maos.record_effect_outcome($1,'UNKNOWN','OUTCOME_UNKNOWN',$2)", intent_id, "3" * 64) == 3
                with pytest.raises(asyncpg.ObjectNotInPrerequisiteStateError):
                    async with runtime.transaction():
                        await runtime.fetchval("SELECT maos.record_effect_outcome($1,'DISPATCHING','BLIND_RETRY',$2)", intent_id, "4" * 64)
                assert await runtime.fetchval("SELECT maos.record_effect_outcome($1,'SUCCEEDED','RECONCILED_ACCEPTED',$2)", intent_id, "5" * 64) == 4
                for privilege in ("SELECT", "UPDATE", "DELETE"):
                    assert not await runtime.fetchval("SELECT has_table_privilege(current_user,'maos.audit_events',$1)", privilege)
                    assert not await runtime.fetchval("SELECT has_table_privilege(current_user,'maos.effect_events',$1)", privilege)
        finally:
            await runtime.close()

        # FORCE RLS is tested as the NOLOGIN table owner, which does not bypass
        # policies. A tenant selector forged away from the canonical resolver
        # returns no rows. Runtime still has no direct table privileges.
        owner = await asyncpg.connect(_admin_db_dsn(db))
        try:
            async with owner.transaction():
                await owner.execute("SET LOCAL ROLE maos_audit_owner")
                await owner.execute("SELECT set_config('maos.principal_user_id','101',true), set_config('maos.tenant_id','tenant-a',true)")
                assert await owner.fetchval("SELECT count(*) FROM maos.operation_reservations") == 3
                assert await owner.fetchval("""
                    SELECT event_hash = encode(sha256(convert_to(jsonb_build_array(previous_hash,tenant_id,
                        sequence,event_id,actor_user_id,action_code,resource_type,resource_id,metadata_digest,
                        correlation_id)::text,'UTF8')),'hex')
                      FROM maos.audit_events WHERE event_id=$1
                """, audit_id) is True
                assert await owner.fetchval("""
                    SELECT provider_idempotency_key = encode(sha256(convert_to($1 || ':' || $2::text,'UTF8')),'hex')
                      FROM maos.effect_intents WHERE intent_id=$3
                """, "tenant-a", str(op_id), intent_id) is True
                assert await owner.fetchval("""
                    SELECT bool_and(c.relrowsecurity AND c.relforcerowsecurity)
                      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                     WHERE n.nspname='maos' AND c.relkind='r'
                """) is True
                assert await owner.fetchval("""
                    SELECT count(*) FROM information_schema.columns WHERE table_schema='maos'
                      AND column_name ~* '(secret|token|password|credential|payload|raw_request)'
                """) == 0
                await owner.execute("SELECT set_config('maos.tenant_id','tenant-b',true)")
                assert await owner.fetchval("SELECT count(*) FROM maos.operation_reservations") == 0
                assert await owner.fetchval("SELECT rolcanlogin OR rolsuper OR rolbypassrls FROM pg_catalog.pg_roles WHERE rolname='maos_audit_owner'") is False
        finally:
            await owner.close()
    finally:
        await _drop_test_db(db, role)
