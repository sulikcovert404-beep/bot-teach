"""Disposable PostgreSQL 16 qualification for MAOS lifecycle persistence.

Run only against a fresh, disposable database whose migration head is 0035:
MAOS_A11_TEST_DSN=postgresql://... pytest tests/maos/test_lifecycle_persistence_postgres.py
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import asyncpg
import pytest

ADMIN_DSN = os.environ.get("MAOS_A11_TEST_DSN", "").strip()
pytestmark = pytest.mark.asyncio


async def _append(
    connection: asyncpg.Connection,
    principal: str,
    from_state: str,
    to_state: str,
    *,
    event_id=None,
    occurred_at: datetime,
) -> int:
    return await connection.fetchval(
        """SELECT maos_lifecycle.append_event(
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10
        )""",
        event_id or uuid4(),
        principal,
        "actor:qualification",
        from_state,
        to_state,
        "reason:qualification",
        "authority:qualification",
        "a" * 64,
        "audit-ref:qualification",
        occurred_at,
    )


async def test_lifecycle_persistence_on_disposable_postgresql_16() -> None:
    if not ADMIN_DSN:
        pytest.skip("MAOS_A11_TEST_DSN must point to a fresh disposable PostgreSQL 16 database")
    admin = await asyncpg.connect(ADMIN_DSN)
    test_role = f"maos_a11_test_{uuid4().hex[:12]}"
    generation = f"a11test_{uuid4().hex[:12]}"
    try:
        facts = await admin.fetchrow(
            "SELECT current_setting('server_version_num')::integer AS version, "
            "(SELECT version_num FROM public.alembic_version) AS revision"
        )
        assert facts["version"] // 10000 == 16
        assert facts["revision"] == "20261006_0035"

        roles = await admin.fetchrow("""
            SELECT owner.rolcanlogin AS owner_login,
                   owner.rolsuper AS owner_super,
                   owner.rolbypassrls AS owner_bypass,
                   writer.rolcanlogin AS writer_login,
                   writer.rolsuper AS writer_super,
                   writer.rolbypassrls AS writer_bypass,
                   pg_catalog.pg_has_role('app_runtime','maos_lifecycle_owner','MEMBER') AS runtime_owner,
                   pg_catalog.pg_has_role('app_runtime','maos_lifecycle_writer','MEMBER') AS runtime_writer,
                   pg_catalog.has_schema_privilege('app_runtime','maos_lifecycle','USAGE') AS runtime_schema,
                   pg_catalog.has_table_privilege('app_runtime','maos_lifecycle.events','SELECT') AS runtime_read,
                   pg_catalog.has_function_privilege(
                       'app_runtime',
                       'maos_lifecycle.append_event(uuid,text,text,text,text,text,text,text,text,timestamp with time zone)',
                       'EXECUTE'
                   ) AS runtime_append
              FROM pg_catalog.pg_roles owner CROSS JOIN pg_catalog.pg_roles writer
             WHERE owner.rolname='maos_lifecycle_owner'
               AND writer.rolname='maos_lifecycle_writer'
        """)
        assert roles is not None
        assert roles["owner_login"] is False and roles["owner_super"] is False and roles["owner_bypass"] is False
        assert roles["writer_login"] is False and roles["writer_super"] is False and roles["writer_bypass"] is False
        assert roles["runtime_owner"] is False and roles["runtime_writer"] is False
        assert roles["runtime_schema"] is False and roles["runtime_read"] is False
        assert roles["runtime_append"] is False

        history_refs = await admin.fetchval("SELECT count(*) FROM maos_lifecycle.events")
        assert history_refs == 0, "qualification requires a fresh disposable database"

        # A11 defines no operational writer login. This synthetic login exists
        # only inside this disposable cluster so function ACLs and the existing
        # A10 database writer fence can be exercised end-to-end.
        await admin.execute(f'CREATE ROLE "{test_role}" LOGIN')
        await admin.execute(f'GRANT maos_lifecycle_writer TO "{test_role}"')
        await admin.execute(
            "INSERT INTO public.ai_teacher_writer_generation_state(generation,database_role,state) "
            "VALUES($1,$2,'SERVING')",
            generation,
            test_role,
        )
        await admin.execute(
            "INSERT INTO public.ai_teacher_writer_generation_state(generation,database_role,state) "
            "VALUES($1,'postgres','SERVING')",
            generation + "_maint",
        )

        # A role switch simulates the test-only control login while retaining a
        # single local disposable connection; session_user is checked by A10.
        await admin.execute(f'SET SESSION AUTHORIZATION "{test_role}"')
        principal = "principal:matrix"
        t0 = datetime.now(UTC).replace(microsecond=0)
        event = uuid4()
        assert await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", principal) == "UNRECONCILED"
        assert await _append(admin, principal, "UNRECONCILED", "ACTIVE", event_id=event, occurred_at=t0) == 1
        assert await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", principal) == "ACTIVE"
        assert await _append(admin, principal, "UNRECONCILED", "ACTIVE", event_id=event, occurred_at=t0) == 1
        with pytest.raises(asyncpg.PostgresError):
            await _append(admin, principal, "ACTIVE", "SUSPENDED", event_id=event, occurred_at=t0)

        assert await _append(admin, principal, "ACTIVE", "SUSPENDED", occurred_at=t0 + timedelta(seconds=1)) == 2
        assert await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", principal) == "SUSPENDED"
        assert await _append(admin, principal, "SUSPENDED", "ACTIVE", occurred_at=t0 + timedelta(seconds=2)) == 3
        assert await _append(admin, principal, "ACTIVE", "DISABLED", occurred_at=t0 + timedelta(seconds=3)) == 4
        assert await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", principal) == "DISABLED"
        for source, target in (("DISABLED", "ACTIVE"), ("DISABLED", "SUSPENDED")):
            with pytest.raises(asyncpg.PostgresError):
                await _append(admin, principal, source, target, occurred_at=t0 + timedelta(seconds=4))
        with pytest.raises(asyncpg.PostgresError):
            await _append(admin, principal, "DISABLED", "UNRECONCILED", occurred_at=t0 + timedelta(seconds=4))

        for start, transitions in (
            ("principal:suspend-first", ("SUSPENDED", "DISABLED")),
            ("principal:disable-first", ("DISABLED",)),
        ):
            source = "UNRECONCILED"
            for index, target in enumerate(transitions, start=10):
                await _append(admin, start, source, target, occurred_at=t0 + timedelta(seconds=index))
                source = target
            assert await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", start) == source
        with pytest.raises(asyncpg.PostgresError):
            await _append(
                admin, "principal:matrix", "DISABLED", "ACTIVE",
                occurred_at=t0 - timedelta(seconds=1),
            )

        # Histories inserted outside the validated append function must fail
        # closed when their first record does not begin at UNRECONCILED.
        class _RollbackQualification(Exception):
            pass

        await admin.execute("RESET SESSION AUTHORIZATION")
        try:
            async with admin.transaction():
                await admin.execute("ALTER TABLE maos_lifecycle.events DISABLE TRIGGER ALL")
                await admin.execute(
                    """INSERT INTO maos_lifecycle.events(
                           event_id,principal_ref,sequence,actor_principal_ref,from_state,to_state,
                           reason_ref,authority_ref,evidence_digest,audit_event_ref,occurred_at,
                           previous_hash,event_hash)
                       VALUES($1,'principal:unanchored',1,'actor:test','ACTIVE','SUSPENDED',
                              'reason:test','authority:test',$2,'audit:test',$3,$4,$4)""",
                    uuid4(), "b" * 64, t0, "0" * 64,
                )
                await admin.execute("ALTER TABLE maos_lifecycle.events ENABLE TRIGGER ALL")
                await admin.execute(f'SET SESSION AUTHORIZATION "{test_role}"')
                try:
                    async with admin.transaction():
                        await admin.fetchval(
                            "SELECT maos_lifecycle.resolve_state('principal:unanchored')"
                        )
                except asyncpg.PostgresError:
                    pass
                else:
                    raise AssertionError("unanchored lifecycle history was accepted")
                finally:
                    await admin.execute("RESET SESSION AUTHORIZATION")
                raise _RollbackQualification
        except _RollbackQualification:
            pass

        # The runtime identity has neither table access nor a resolver/writer
        # function grant; it cannot self-activate even with caller-controlled SQL.
        await admin.execute("RESET SESSION AUTHORIZATION")
        await admin.execute("SET ROLE app_runtime")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await admin.fetchval("SELECT state FROM maos_lifecycle.current_state_projection LIMIT 1")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await admin.fetchval("SELECT maos_lifecycle.resolve_state('principal:matrix')")
        await admin.execute("RESET ROLE")

        # Corrupt only the disposable projection under test-administrator
        # authority; the public resolver must refuse its inconsistent state.
        await admin.execute("ALTER TABLE maos_lifecycle.current_state_projection DISABLE TRIGGER ALL")
        await admin.execute(
            "UPDATE maos_lifecycle.current_state_projection SET state='ACTIVE' WHERE principal_ref=$1",
            principal,
        )
        await admin.execute("ALTER TABLE maos_lifecycle.current_state_projection ENABLE TRIGGER ALL")
        await admin.execute(f'SET SESSION AUTHORIZATION "{test_role}"')
        with pytest.raises(asyncpg.PostgresError):
            await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", principal)
        await admin.execute("RESET SESSION AUTHORIZATION")
        assert await admin.fetchval("SELECT maos_lifecycle.rebuild_projection()") >= 3
        await admin.execute(f'SET SESSION AUTHORIZATION "{test_role}"')
        assert await admin.fetchval("SELECT maos_lifecycle.resolve_state($1)", principal) == "DISABLED"
        await admin.execute("RESET SESSION AUTHORIZATION")

        # Event rows reject UPDATE, DELETE and TRUNCATE, even for the synthetic
        # writer; account identity is a text reference and cannot cascade-delete.
        await admin.execute(f'SET SESSION AUTHORIZATION "{test_role}"')
        with pytest.raises(asyncpg.PostgresError):
            await admin.execute(
                "UPDATE maos_lifecycle.events SET reason_ref='changed' WHERE principal_ref=$1",
                principal,
            )
        with pytest.raises(asyncpg.PostgresError):
            await admin.execute("DELETE FROM maos_lifecycle.events WHERE principal_ref=$1", principal)
        with pytest.raises(asyncpg.PostgresError):
            await admin.execute("TRUNCATE maos_lifecycle.events")
        await admin.execute("RESET SESSION AUTHORIZATION")
        event_count = await admin.fetchval(
            "SELECT count(*) FROM maos_lifecycle.events WHERE principal_ref=$1", principal
        )
        assert event_count == 4

        user_id = await admin.fetchval("INSERT INTO public.users(role) VALUES('STUDENT') RETURNING id")
        await admin.execute(f'SET SESSION AUTHORIZATION "{test_role}"')
        await _append(
            admin, f"user:{user_id}", "UNRECONCILED", "ACTIVE", occurred_at=t0 + timedelta(minutes=1)
        )
        await admin.execute("RESET SESSION AUTHORIZATION")
        await admin.execute("DELETE FROM public.users WHERE id=$1", user_id)
        assert await admin.fetchval(
            "SELECT count(*) FROM maos_lifecycle.events WHERE principal_ref=$1", f"user:{user_id}"
        ) == 1
    finally:
        try:
            await admin.execute("RESET SESSION AUTHORIZATION")
            await admin.execute("RESET ROLE")
            await admin.execute(
                "DELETE FROM public.ai_teacher_writer_generation_state WHERE generation = ANY($1::text[])",
                [generation, generation + "_maint"],
            )
            await admin.execute(f'REVOKE maos_lifecycle_writer FROM "{test_role}"')
            await admin.execute(f'DROP ROLE IF EXISTS "{test_role}"')
        finally:
            await admin.close()
