"""Disposable PostgreSQL qualification harness for Gate MAOS-A12TGI.

Run only against a disposable PostgreSQL 16 database after explicitly upgrading
through 20261006_0035 and then the candidate 20261007_0036 revision. The harness
refuses non-loopback or non-A12TGI database URLs. It creates and removes only
its uniquely named fixtures in that disposable database.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from urllib.parse import urlparse

import asyncpg


def _dsn(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    parsed = urlparse(value)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or "a12tgi" not in (parsed.path or "").lower():
        raise RuntimeError(f"{name} must point to a loopback disposable A12TGI database")
    return value


ADMIN_DSN = _dsn("GATE_MAOS_A12TGI_ADMIN_URL")
RUNTIME_DSN = _dsn("GATE_MAOS_A12TGI_RUNTIME_URL")
PREFIX = "a12tgi_" + uuid.uuid4().hex[:10]
IDEMPOTENCY_KEYS: list[str] = []
FIXTURES: list[dict[str, object]] = []


async def admin_connect() -> asyncpg.Connection:
    return await asyncpg.connect(ADMIN_DSN, server_settings={"application_name": "a12tgi-admin"})


async def runtime_connect(application_name: str) -> asyncpg.Connection:
    conn = await asyncpg.connect(RUNTIME_DSN, server_settings={"application_name": application_name})
    await conn.execute("SET ROLE app_runtime")
    return conn


async def fixture(*, membership: bool = True, second_membership: bool = False) -> dict[str, object]:
    conn = await admin_connect()
    try:
        actor_id, user_id = await conn.fetchrow(
            "SELECT nextval('public.users_id_seq')::integer, nextval('public.users_id_seq')::integer"
        )
        tenant = f"{PREFIX}_{len(FIXTURES)}"
        await conn.execute("BEGIN")
        await conn.execute("SET LOCAL session_replication_role = replica")
        await conn.execute(
            "INSERT INTO public.users(id,username,role) VALUES($1,$2,'SUPER_ADMIN'),($3,$4,'STUDENT')",
            actor_id,
            f"{tenant}_admin",
            user_id,
            f"{tenant}_user",
        )
        await conn.execute("INSERT INTO public.school_tenants(tenant_id,school_name) VALUES($1,$2)", tenant, tenant)
        if membership:
            await conn.execute(
                "INSERT INTO public.user_tenant_memberships(user_id,tenant_id,status,created_by) VALUES($1,$2,'ACTIVE',$3)",
                user_id,
                tenant,
                actor_id,
            )
        if second_membership:
            other = f"{tenant}_ambiguous"
            await conn.execute("INSERT INTO public.school_tenants(tenant_id,school_name) VALUES($1,$1)", other)
            await conn.execute(
                "INSERT INTO public.user_tenant_memberships(user_id,tenant_id,status,created_by) VALUES($1,$2,'ACTIVE',$3)",
                user_id,
                other,
                actor_id,
            )
        await conn.execute("INSERT INTO public.exams(user_id,title,tenant_id) VALUES($1,$2,$3)", user_id, tenant, tenant)
        await conn.execute("COMMIT")
        result = {"actor_id": actor_id, "user_id": user_id, "tenant": tenant}
        FIXTURES.append(result)
        return result
    finally:
        await conn.close()


async def lease(conn: asyncpg.Connection, user_id: int, tenant: str) -> tuple[bool, bool]:
    # Keep these as distinct SQL commands: validation must start with a new
    # READ COMMITTED statement snapshot after any advisory-lock wait.
    acquired = await conn.fetchval(
        "SELECT public.acquire_public_tenant_membership_lease($1,$2)", user_id, tenant
    )
    validated = await conn.fetchval(
        "SELECT public.validate_public_tenant_membership_lease($1,$2)", user_id, tenant
    )
    return bool(acquired), bool(validated)


async def assert_context_denied(
    conn: asyncpg.Connection,
    tenant: str,
    changes: dict[str, str | None],
    baseline: dict[str, str],
    label: str,
) -> None:
    for setting, value in changes.items():
        if value is None:
            await conn.execute(f"RESET {setting}")
        else:
            await conn.execute("SELECT set_config($1,$2,true)", setting, value)
    assert not await conn.fetchval(
        "SELECT public.has_public_tenant_membership_lease($1)", tenant
    ), f"invalid context passed the lease helper: {label}"
    assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0, (
        f"invalid context passed public RLS: {label}"
    )
    for setting, value in baseline.items():
        await conn.execute("SELECT set_config($1,$2,true)", setting, value)


async def revoke(conn: asyncpg.Connection, item: dict[str, object], suffix: str) -> str:
    key = f"{PREFIX}_revoke_{suffix}"
    IDEMPOTENCY_KEYS.append(key)
    result = await conn.fetchval(
        "SELECT public.revoke_tenant_membership($1,$2,$3::jsonb,$4,$5,$6)",
        item["actor_id"],
        "SUPER_ADMIN",
        json.dumps({"user_id": item["user_id"], "tenant_id": item["tenant"]}),
        f"{PREFIX}_{suffix}_fingerprint",
        key,
        f"{PREFIX}_{suffix}_correlation",
    )
    return str(result)


async def wait_for_lock_wait(application_name: str, timeout: float = 4.0) -> bool:
    admin = await admin_connect()
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            row = await admin.fetchrow(
                "SELECT wait_event_type,wait_event FROM pg_catalog.pg_stat_activity WHERE application_name=$1",
                application_name,
            )
            if row and row["wait_event_type"] == "Lock":
                return True
            await asyncio.sleep(0.04)
        return False
    finally:
        await admin.close()


async def cleanup() -> None:
    conn = await admin_connect()
    try:
        await conn.execute("REVOKE app_runtime FROM a12tgi_candidate")
        await conn.execute("REVOKE ALL ON public.exams FROM app_runtime")
        await conn.execute("REVOKE ALL ON SEQUENCE public.exams_id_seq FROM app_runtime")
        await conn.execute("BEGIN")
        await conn.execute("SET LOCAL session_replication_role = replica")
        if IDEMPOTENCY_KEYS:
            await conn.execute(
                "DELETE FROM public.provisioning_idempotency_keys WHERE idempotency_key = ANY($1::text[])",
                IDEMPOTENCY_KEYS,
            )
        for item in reversed(FIXTURES):
            actor_id = int(item["actor_id"])
            user_id = int(item["user_id"])
            tenant = str(item["tenant"])
            await conn.execute(
                "DELETE FROM public.audit_logs WHERE actor_user_id=$1 AND resource_id=$2",
                actor_id,
                str(user_id),
            )
            await conn.execute("DELETE FROM public.exams WHERE user_id=$1 AND tenant_id LIKE $2", user_id, tenant + "%")
            await conn.execute("DELETE FROM public.user_tenant_memberships WHERE user_id=$1", user_id)
            await conn.execute("DELETE FROM public.school_tenants WHERE tenant_id LIKE $1", tenant + "%")
            await conn.execute("DELETE FROM public.users WHERE id=ANY($1::integer[])", [actor_id, user_id])
        await conn.execute("COMMIT")
    finally:
        await conn.close()


async def qualify() -> dict[str, object]:
    admin = await admin_connect()
    try:
        version = await admin.fetchval("SELECT version_num FROM public.alembic_version")
        assert version == "20261007_0036", f"expected candidate revision 0036; found {version!r}"
        assert await admin.fetchval(
            "SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname='tenant_lease_owner' "
            "AND NOT (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole "
            "OR rolinherit OR rolreplication OR rolbypassrls)"
        ) == 1, "lease owner must have exactly the inert role attributes"
        assert await admin.fetchval(
            "SELECT count(*) FROM pg_catalog.pg_auth_members m "
            "JOIN pg_catalog.pg_roles r ON (r.oid=m.roleid OR r.oid=m.member) "
            "WHERE r.rolname='tenant_lease_owner'"
        ) == 0, "lease owner must have zero inbound and outbound memberships"
        await admin.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON public.exams TO app_runtime")
        await admin.execute("GRANT USAGE,SELECT ON SEQUENCE public.exams_id_seq TO app_runtime")
        assert not await admin.fetchval(
            "SELECT has_table_privilege('app_runtime','public.user_tenant_memberships','SELECT,INSERT,UPDATE,DELETE')"
        ), "app_runtime must not receive direct membership-table privileges"
        policy_count = await admin.fetchval(
            "SELECT count(*) FROM pg_catalog.pg_policies WHERE schemaname='public' "
            "AND qual ILIKE '%has_public_tenant_membership_lease%' "
            "AND with_check ILIKE '%has_public_tenant_membership_lease%'"
        )
        assert policy_count == 12, f"expected 12 protected public RLS policies, saw {policy_count}"
        writer_locks: dict[str, bool] = {}
        for name in (
            "bootstrap_school_tenant",
            "provision_tenant_membership",
            "revoke_tenant_membership",
        ):
            definition = await admin.fetchval(
                "SELECT pg_get_functiondef(p.oid) FROM pg_catalog.pg_proc p "
                "JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace "
                "WHERE n.nspname='public' AND p.proname=$1",
                name,
            )
            assert definition and "pg_advisory_xact_lock(" in definition
            assert "tenant-membership-user:" in definition
            writer_locks[name] = True
        for signature in (
            "public.acquire_public_tenant_membership_lease(integer,text)",
            "public.validate_public_tenant_membership_lease(integer,text)",
            "public.has_public_tenant_membership_lease(text)",
        ):
            assert await admin.fetchval("SELECT NOT has_function_privilege('public',$1,'EXECUTE')", signature)
            assert await admin.fetchval("SELECT has_function_privilege('app_runtime',$1,'EXECUTE')", signature)
            owner = await admin.fetchval("SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid=$1::regprocedure", signature)
            assert owner == "tenant_lease_owner", (signature, owner)
        await admin.execute("GRANT app_runtime TO a12tgi_candidate")
    finally:
        await admin.close()

    report: dict[str, object] = {
        "baseline_version": version,
        "policies": policy_count,
        "function_acl_and_owner": "PASS",
        "canonical_exclusive_lock_paths": writer_locks,
        "app_runtime_membership_table_privileges": "NONE",
    }

    # A GUC by itself, including the ordinary tenant context, grants nothing.
    item = await fixture()
    conn = await runtime_connect("a12tgi-forged-guc")
    try:
        forged_tx = conn.transaction(isolation="read_committed")
        await forged_tx.start()
        await conn.execute("SELECT set_config('app.tenant_id',$1,true)", item["tenant"])
        await conn.execute("SELECT set_config('app.user_id',$1,true)", str(item["user_id"]))
        assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0
        assert await conn.fetchval(
            "SELECT public.has_public_tenant_membership_lease($1)", item["tenant"]
        ) is False
        try:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO public.exams(user_id,title,tenant_id) VALUES($1,$2,$3)",
                    item["user_id"],
                    "forged context must not write",
                    item["tenant"],
                )
        except asyncpg.InsufficientPrivilegeError:
            pass
        else:
            raise AssertionError("GUC-only context unexpectedly passed the RLS write check")
        await forged_tx.rollback()
    finally:
        await conn.close()
    report["forged_guc_only"] = "DENIED for SELECT and INSERT"

    # Successful validation and transaction-local connection reuse boundaries.
    conn = await runtime_connect("a12tgi-valid-context")
    try:
        tx = conn.transaction(isolation="read_committed")
        await tx.start()
        acquired, validated = await lease(conn, int(item["user_id"]), str(item["tenant"]))
        assert acquired and validated
        assert await conn.fetchval("SELECT count(*) FROM public.exams") == 1
        assert await conn.fetchval("SELECT public.has_public_tenant_membership_lease($1)", item["tenant"])
        await conn.execute(
            "INSERT INTO public.exams(user_id,title,tenant_id) VALUES($1,$2,$3)",
            item["user_id"],
            "A12TGI RLS write",
            item["tenant"],
        )
        user_id = int(item["user_id"])
        tenant = str(item["tenant"])
        valid_context = {
            "app.user_id": str(user_id),
            "app.public_membership_lease_validated_user_id": str(user_id),
            "app.public_membership_lease_user_id": str(user_id),
            "app.tenant_id": tenant,
            "app.public_membership_lease_tenant_id": tenant,
            "app.public_membership_lease_validated_tenant_id": tenant,
        }
        invalid_contexts: tuple[tuple[str, dict[str, str | None]], ...] = (
            ("missing app.user_id", {"app.user_id": None}),
            ("empty app.user_id", {"app.user_id": ""}),
            ("missing validated principal", {"app.public_membership_lease_validated_user_id": None}),
            ("empty validated principal", {"app.public_membership_lease_validated_user_id": ""}),
            ("both principal markers missing", {
                "app.user_id": None,
                "app.public_membership_lease_validated_user_id": None,
            }),
            ("both principal markers empty", {
                "app.user_id": "",
                "app.public_membership_lease_validated_user_id": "",
            }),
            ("missing lease principal", {"app.public_membership_lease_user_id": None}),
            ("empty lease principal", {"app.public_membership_lease_user_id": ""}),
            ("app principal mismatch", {"app.user_id": str(user_id + 10)}),
            ("lease principal mismatch", {"app.public_membership_lease_user_id": str(user_id + 10)}),
            ("malformed app principal", {"app.user_id": "not-an-integer"}),
            ("non-positive app principal", {"app.user_id": "0"}),
            ("malformed validated principal", {
                "app.public_membership_lease_validated_user_id": "not-an-integer",
            }),
            ("non-positive validated principal", {
                "app.public_membership_lease_validated_user_id": "0",
            }),
            ("malformed lease principal", {
                "app.public_membership_lease_user_id": "not-an-integer",
            }),
            ("non-positive lease principal", {"app.public_membership_lease_user_id": "-1"}),
            ("held lock does not match claimed principal", {
                "app.user_id": str(user_id + 10),
                "app.public_membership_lease_validated_user_id": str(user_id + 10),
                "app.public_membership_lease_user_id": str(user_id + 10),
            }),
            ("missing tenant context", {"app.tenant_id": None}),
            ("empty tenant context", {"app.tenant_id": ""}),
            ("missing lease tenant", {"app.public_membership_lease_tenant_id": None}),
            ("empty lease tenant", {"app.public_membership_lease_tenant_id": ""}),
            ("missing validated tenant", {
                "app.public_membership_lease_validated_tenant_id": None,
            }),
            ("empty validated tenant", {
                "app.public_membership_lease_validated_tenant_id": "",
            }),
            ("active tenant mismatch", {"app.tenant_id": f"{tenant}_other"}),
            ("lease tenant mismatch", {
                "app.public_membership_lease_tenant_id": f"{tenant}_other",
            }),
            ("validated tenant mismatch", {
                "app.public_membership_lease_validated_tenant_id": f"{tenant}_other",
            }),
        )
        for label, changes in invalid_contexts:
            await assert_context_denied(conn, tenant, changes, valid_context, label)
        await tx.commit()
        lock_key = await conn.fetchval(
            "SELECT hashtextextended('tenant-membership-user:' || $1::integer::text,0)", item["user_id"]
        )
        assert await conn.fetchval(
            "SELECT count(*) FROM pg_catalog.pg_locks WHERE locktype='advisory' "
            "AND pid=pg_backend_pid() AND objsubid=1 "
            "AND ((classid::bigint << 32) | objid::bigint)=$1",
            lock_key,
        ) == 0
        tx2 = conn.transaction(isolation="read_committed")
        await tx2.start()
        assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0
        await tx2.rollback()
    finally:
        await conn.close()
    report["lease_and_rls_write"] = "PASS"
    report["principal_and_tenant_context_binding"] = "PASS: missing, empty, malformed, non-positive, mismatched, and wrong-lock contexts denied"
    report["connection_reuse"] = "PASS"

    # Wrong user/tenant and unsupported isolation levels fail closed.
    conn = await runtime_connect("a12tgi-wrong-context")
    try:
        tx = conn.transaction(isolation="read_committed")
        await tx.start()
        assert await conn.fetchval(
            "SELECT public.acquire_public_tenant_membership_lease($1,$2)", item["user_id"], item["tenant"]
        )
        assert not await conn.fetchval(
            "SELECT public.validate_public_tenant_membership_lease($1,$2)", int(item["user_id"]) + 10, item["tenant"]
        )
        assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0
        await tx.rollback()
        for isolation in ("repeatable_read", "serializable"):
            tx = conn.transaction(isolation=isolation)
            await tx.start()
            assert not await conn.fetchval(
                "SELECT public.acquire_public_tenant_membership_lease($1,$2)", item["user_id"], item["tenant"]
            )
            assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0
            await tx.rollback()
    finally:
        await conn.close()
    report["wrong_user_and_higher_isolation"] = "DENIED"
    report["repeatable_read"] = "DENIED"
    report["serializable"] = "DENIED"
    report["owner_attributes_and_zero_memberships"] = "PASS"

    # Protected transaction wins: canonical revoke must wait for the lease.
    winner = await fixture()
    protected = await runtime_connect("a12tgi-protected-wins")
    writer = await runtime_connect("a12tgi-revoke-waits")
    ptx = protected.transaction(isolation="read_committed")
    await ptx.start()
    acquired, validated = await lease(protected, int(winner["user_id"]), str(winner["tenant"]))
    assert acquired and validated
    assert await protected.fetchval("SELECT count(*) FROM public.exams") == 1
    lock_rows = await protected.fetch(
        "SELECT classid,objid,objsubid,mode,granted FROM pg_catalog.pg_locks "
        "WHERE locktype='advisory' AND pid=pg_backend_pid() AND objsubid=1"
    )
    assert any(row["mode"] == "ShareLock" and row["granted"] for row in lock_rows)
    await writer.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
    revoke_task = asyncio.create_task(revoke(writer, winner, "protected_wins"))
    assert await wait_for_lock_wait("a12tgi-revoke-waits"), "revoke did not wait on protected membership lease"
    await ptx.commit()
    revoke_result = await revoke_task
    await writer.execute("COMMIT")
    assert "REVOKED" in revoke_result
    assert await protected.fetchval("SELECT public.resolve_tenant($1)", winner["user_id"]) is None
    await protected.close()
    await writer.close()
    report["protected_lease_wins"] = "PASS: revoke blocked until protected transaction committed"

    # Mutation wins: a waiting protected request gets a fresh snapshot and denies.
    mutation = await fixture()
    writer = await runtime_connect("a12tgi-mutation-wins")
    protected = await runtime_connect("a12tgi-protected-waits")
    await writer.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
    revoke_result = await revoke(writer, mutation, "mutation_wins")
    assert "REVOKED" in revoke_result
    ptx = protected.transaction(isolation="read_committed")
    await ptx.start()
    acquire_task = asyncio.create_task(
        protected.fetchval(
            "SELECT public.acquire_public_tenant_membership_lease($1,$2)",
            mutation["user_id"],
            mutation["tenant"],
        )
    )
    assert await wait_for_lock_wait("a12tgi-protected-waits"), "protected request did not wait on revocation"
    await writer.execute("COMMIT")
    assert await acquire_task
    assert not await protected.fetchval(
        "SELECT public.validate_public_tenant_membership_lease($1,$2)", mutation["user_id"], mutation["tenant"]
    )
    assert await protected.fetchval("SELECT count(*) FROM public.exams") == 0
    await ptx.rollback()
    await writer.close()
    await protected.close()
    report["mutation_wins_fresh_snapshot"] = "PASS: waiting request validated after commit and was denied"

    # Ambiguous and suspended membership states never validate.
    ambiguous = await fixture(second_membership=True)
    conn = await admin_connect()
    try:
        assert await conn.fetchval("SELECT public.resolve_tenant($1)", ambiguous["user_id"]) is None
    finally:
        await conn.close()
    conn = await runtime_connect("a12tgi-ambiguous")
    try:
        tx = conn.transaction(isolation="read_committed")
        await tx.start()
        assert await conn.fetchval(
            "SELECT public.acquire_public_tenant_membership_lease($1,$2)", ambiguous["user_id"], ambiguous["tenant"]
        )
        assert not await conn.fetchval(
            "SELECT public.validate_public_tenant_membership_lease($1,$2)", ambiguous["user_id"], ambiguous["tenant"]
        )
        assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0
        await tx.rollback()
    finally:
        await conn.close()
    report["ambiguous_membership"] = "DENIED"

    suspended = await fixture()
    conn = await admin_connect()
    try:
        await conn.execute("BEGIN")
        await conn.execute("SET LOCAL session_replication_role = replica")
        await conn.execute(
            "UPDATE public.user_tenant_memberships SET status='SUSPENDED' WHERE user_id=$1 AND tenant_id=$2",
            suspended["user_id"],
            suspended["tenant"],
        )
        await conn.execute("COMMIT")
    finally:
        await conn.close()
    conn = await runtime_connect("a12tgi-suspended")
    try:
        tx = conn.transaction(isolation="read_committed")
        await tx.start()
        assert await conn.fetchval(
            "SELECT public.acquire_public_tenant_membership_lease($1,$2)", suspended["user_id"], suspended["tenant"]
        )
        assert not await conn.fetchval(
            "SELECT public.validate_public_tenant_membership_lease($1,$2)", suspended["user_id"], suspended["tenant"]
        )
        assert await conn.fetchval("SELECT count(*) FROM public.exams") == 0
        await tx.rollback()
    finally:
        await conn.close()
    report["suspended_membership"] = "DENIED (fixture state; no canonical suspend API exists at 0035)"

    rolled_back = await fixture()
    writer = await runtime_connect("a12tgi-mutation-rollback")
    await writer.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
    rolled_back_result = await revoke(writer, rolled_back, "rollback")
    assert "REVOKED" in rolled_back_result
    await writer.execute("ROLLBACK")
    check = await admin_connect()
    try:
        assert await check.fetchval("SELECT public.resolve_tenant($1)", rolled_back["user_id"]) == rolled_back["tenant"]
    finally:
        await check.close()
    await writer.close()
    report["mutation_rollback"] = "PASS: membership remained active; writer lock released at rollback"

    # Canonical provisioning uses the same exclusive per-principal advisory key.
    unprovisioned = await fixture(membership=False)
    protected = await runtime_connect("a12tgi-provision-protected")
    writer = await runtime_connect("a12tgi-provision-waits")
    ptx = protected.transaction(isolation="read_committed")
    await ptx.start()
    assert await protected.fetchval(
        "SELECT public.acquire_public_tenant_membership_lease($1,$2)", unprovisioned["user_id"], unprovisioned["tenant"]
    )
    assert not await protected.fetchval(
        "SELECT public.validate_public_tenant_membership_lease($1,$2)", unprovisioned["user_id"], unprovisioned["tenant"]
    )
    await writer.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
    key = f"{PREFIX}_provision_waits"
    IDEMPOTENCY_KEYS.append(key)
    provision_task = asyncio.create_task(
        writer.fetchval(
            "SELECT public.provision_tenant_membership($1,$2,$3::jsonb,$4,$5,$6)",
            unprovisioned["actor_id"],
            "SUPER_ADMIN",
            json.dumps({"user_id": unprovisioned["user_id"], "tenant_id": unprovisioned["tenant"], "role": "STUDENT"}),
            f"{PREFIX}_provision_fingerprint",
            key,
            f"{PREFIX}_provision_correlation",
        )
    )
    assert await wait_for_lock_wait("a12tgi-provision-waits"), "provision did not wait for principal lease"
    await ptx.commit()
    provision_result = await provision_task
    await writer.execute("COMMIT")
    assert "CREATED" in str(provision_result)
    check = await admin_connect()
    try:
        assert await check.fetchval("SELECT public.resolve_tenant($1)", unprovisioned["user_id"]) == unprovisioned["tenant"]
    finally:
        await check.close()
    await protected.close()
    await writer.close()
    report["provision_mutation_lock"] = "PASS"
    report["deadlock"] = "None observed during both lock-order concurrency cases"
    return report


async def main() -> None:
    try:
        report = await qualify()
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
