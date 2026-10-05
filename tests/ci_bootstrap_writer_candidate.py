"""Bootstrap and verify the disposable writer candidate used only by CI."""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from ci_bootstrap_app_runtime import (
    _attest_service_container_address,
    _server_address_matches,
    validate_database_url,
)


class CandidateBootstrapError(RuntimeError):
    """Fail-closed CI-only candidate role error."""


_SOURCE_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_ROLE = re.compile(r"\Agpc_[0-9a-f]{12}_[12]\Z")
_GENERATION = re.compile(r"\Aci_[0-9a-f]{12}_[12]\Z")


def _candidate_names() -> tuple[str, str]:
    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    replay = os.environ.get("GATE738P_REPLAY_ID", "").strip()
    if not _SOURCE_SHA.fullmatch(source_sha) or replay not in {"1", "2"}:
        raise CandidateBootstrapError("SOURCE_OR_REPLAY_ID_INVALID")
    try:
        checkout_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise CandidateBootstrapError("CHECKOUT_SOURCE_IDENTITY_UNAVAILABLE") from None
    if checkout_sha != source_sha:
        raise CandidateBootstrapError("CHECKOUT_SOURCE_IDENTITY_MISMATCH")
    role = f"gpc_{source_sha[:12]}_{replay}"
    generation = f"ci_{source_sha[:12]}_{replay}"
    if not _ROLE.fullmatch(role) or not _GENERATION.fullmatch(generation):
        raise CandidateBootstrapError("CANDIDATE_IDENTIFIER_INVALID")
    return role, generation


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    try:
        validate_database_url(value)
    except Exception as exc:
        raise CandidateBootstrapError("DATABASE_TARGET_NOT_DEDICATED_CI_POSTGRES") from exc
    return value


async def _connect_verified():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise CandidateBootstrapError("GITHUB_ACTIONS_REQUIRED")
    database_url = _database_url()
    try:
        address = _attest_service_container_address(
            os.environ.get("CI_POSTGRES_SERVICE_ID")
        )
        connection = await asyncpg.connect(
            database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        )
    except Exception as exc:
        raise CandidateBootstrapError("CI_SERVICE_IDENTITY_ATTESTATION_FAILED") from exc
    identity = await connection.fetchrow("""
        SELECT current_user, session_user, current_database() AS database_name,
               inet_server_addr() AS server_address,
               actor.rolsuper AS actor_superuser
          FROM pg_catalog.pg_roles AS actor
         WHERE actor.rolname = current_user
    """)
    if (
        identity is None
        or identity["current_user"] != "ci_migrations"
        or identity["session_user"] != "ci_migrations"
        or identity["database_name"] != "ai_teacher_migrations"
        or not _server_address_matches(identity["server_address"], address)
        or identity["actor_superuser"] is not True
    ):
        await connection.close()
        raise CandidateBootstrapError("DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES")
    return connection


async def _app_runtime_attributes(connection) -> None:
    role = await connection.fetchrow("""
        SELECT rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
               rolreplication, rolbypassrls
          FROM pg_catalog.pg_roles WHERE rolname='app_runtime'
    """)
    expected = (True, True, False, False, False, False, False)
    if role is None or tuple(role.values()) != expected:
        raise CandidateBootstrapError("APP_RUNTIME_ROLE_ATTRIBUTES_MISMATCH")
    memberships = await connection.fetchval("""
        SELECT count(*) FROM pg_catalog.pg_auth_members AS membership
          JOIN pg_catalog.pg_roles AS member ON member.oid=membership.member
         WHERE member.rolname='app_runtime'
    """)
    if memberships != 0:
        raise CandidateBootstrapError("APP_RUNTIME_ROLE_MEMBERSHIP_NOT_EMPTY")


async def _verify_candidate(connection, role_name: str, generation: str) -> None:
    role = await connection.fetchrow("""
        SELECT rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
               rolreplication, rolbypassrls
          FROM pg_catalog.pg_roles WHERE rolname=$1
    """, role_name)
    expected = (True, True, False, False, False, False, False)
    if role is None or tuple(role.values()) != expected:
        raise CandidateBootstrapError("CANDIDATE_ROLE_ATTRIBUTES_MISMATCH")
    memberships = await connection.fetch("""
        SELECT granted.rolname
          FROM pg_catalog.pg_auth_members AS membership
          JOIN pg_catalog.pg_roles AS member ON member.oid=membership.member
          JOIN pg_catalog.pg_roles AS granted ON granted.oid=membership.roleid
         WHERE member.rolname=$1 ORDER BY granted.rolname
    """, role_name)
    if [row["rolname"] for row in memberships] != ["app_runtime"]:
        raise CandidateBootstrapError("CANDIDATE_ROLE_MEMBERSHIP_MISMATCH")
    can_assume_candidate = await connection.fetchval(
        "SELECT pg_catalog.pg_has_role('app_runtime', $1, 'MEMBER')", role_name
    )
    if can_assume_candidate:
        raise CandidateBootstrapError("APP_RUNTIME_CAN_ASSUME_CANDIDATE")


async def bootstrap() -> tuple[str, str]:
    role_name, generation = _candidate_names()
    connection = await _connect_verified()
    try:
        await _app_runtime_attributes(connection)
        existing = await connection.fetchval(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=$1", role_name
        )
        if existing is not None:
            raise CandidateBootstrapError("CANDIDATE_ROLE_ALREADY_EXISTS")
        async with connection.transaction():
            await connection.execute(
                f'CREATE ROLE "{role_name}" LOGIN INHERIT NOSUPERUSER '
                "NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
            )
            await connection.execute(f'GRANT app_runtime TO "{role_name}"')
        await _verify_candidate(connection, role_name, generation)
    finally:
        await connection.close()
    output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not output:
        raise CandidateBootstrapError("GITHUB_OUTPUT_REQUIRED")
    await asyncio.to_thread(_append_github_output, output, role_name, generation)
    return role_name, generation


def _append_github_output(output: str, role_name: str, generation: str) -> None:
    with Path(output).open("a", encoding="utf-8") as handle:
        handle.write(f"writer_role={role_name}\nwriter_generation={generation}\n")


async def assert_contract() -> None:
    role_name, generation = _candidate_names()
    connection = await _connect_verified()
    try:
        await _app_runtime_attributes(connection)
        await _verify_candidate(connection, role_name, generation)
        head = await connection.fetchval("SELECT version_num FROM public.alembic_version")
        if head != "20261004_0032":
            raise CandidateBootstrapError("CLASS_A_MIGRATION_HEAD_MISMATCH")
        vector_version = await connection.fetchval(
            "SELECT extversion FROM pg_catalog.pg_extension WHERE extname='vector'"
        )
        if not vector_version:
            raise CandidateBootstrapError("PGVECTOR_EXTENSION_NOT_INSTALLED_AFTER_CLASS_A")

        state_relation = await connection.fetchval(
            "SELECT pg_catalog.to_regclass('public.ai_teacher_writer_generation_state')"
        )
        if state_relation is None:
            raise CandidateBootstrapError("WRITER_STATE_TABLE_MISSING")
        states = await connection.fetch("""
            SELECT generation, database_role, state
              FROM public.ai_teacher_writer_generation_state
             WHERE generation IN ('legacy',$1)
             ORDER BY generation
        """, generation)
        expected_states = {
            ("legacy", "app_runtime", "SERVING"),
            (generation, role_name, "SERVING"),
        }
        if {tuple(row.values()) for row in states} != expected_states:
            raise CandidateBootstrapError("WRITER_GENERATION_STATE_MISMATCH")

        constraints = await connection.fetchval("""
            SELECT count(*) FROM pg_catalog.pg_constraint AS c
              JOIN pg_catalog.pg_class AS r ON r.oid=c.conrelid
              JOIN pg_catalog.pg_namespace AS n ON n.oid=r.relnamespace
             WHERE n.nspname='public'
               AND r.relname='ai_teacher_writer_generation_state'
               AND c.conname IN ('ck_ai_writer_generation_id','ck_ai_writer_generation_state')
        """)
        if constraints != 2:
            raise CandidateBootstrapError("WRITER_STATE_CONSTRAINTS_MISSING")

        functions = await connection.fetch("""
            SELECT p.proname, p.prosecdef, p.proconfig,
                   EXISTS (
                     SELECT 1 FROM pg_catalog.aclexplode(
                       COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))
                     ) AS acl WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
                   ) AS public_execute
              FROM pg_catalog.pg_proc AS p
              JOIN pg_catalog.pg_namespace AS n ON n.oid=p.pronamespace
             WHERE n.nspname='public'
               AND p.proname IN ('gate738k_admit_writer','gate738k_guard_writer')
        """)
        if len(functions) != 2 or any(
            row["prosecdef"] is not True
            or "search_path=pg_catalog" not in (row["proconfig"] or [])
            or row["public_execute"] is not False
            for row in functions
        ):
            raise CandidateBootstrapError("WRITER_ADMISSION_FUNCTION_CONTRACT_MISMATCH")

        trigger_coverage = await connection.fetchrow("""
            SELECT count(*) AS expected_count,
                   count(*) FILTER (WHERE t.oid IS NOT NULL) AS covered_count
              FROM pg_catalog.pg_class AS r
              JOIN pg_catalog.pg_namespace AS n ON n.oid=r.relnamespace
              LEFT JOIN pg_catalog.pg_trigger AS t
                ON t.tgrelid=r.oid AND t.tgname='gate738k_writer_fence' AND NOT t.tgisinternal
             WHERE n.nspname='public' AND r.relkind IN ('r','p')
               AND r.relname NOT IN ('alembic_version','ai_teacher_writer_generation_state',
                                     'submission_revision_backfill_state',
                                     'submission_revision_rollout_state')
        """)
        if (
            trigger_coverage["expected_count"] == 0
            or trigger_coverage["covered_count"] != trigger_coverage["expected_count"]
        ):
            raise CandidateBootstrapError("WRITER_FENCE_TRIGGER_COVERAGE_MISMATCH")

        public_table_grants = await connection.fetchval("""
            SELECT EXISTS (
              SELECT 1 FROM pg_catalog.aclexplode(
                COALESCE(c.relacl, pg_catalog.acldefault('r', c.relowner))
              ) AS acl
              WHERE c.oid='public.ai_teacher_writer_generation_state'::regclass
                AND acl.grantee=0
            )
        """)
        if public_table_grants:
            raise CandidateBootstrapError("WRITER_STATE_PUBLIC_PRIVILEGE_NOT_REVOKED")
    finally:
        await connection.close()


async def main() -> None:
    try:
        if sys.argv[1:] == ["--assert-contract"]:
            await assert_contract()
            print("Verified Gate738K disposable DB contract at 20261004_0032.")
        elif not sys.argv[1:]:
            role, generation = await bootstrap()
            print(f"Verified disposable candidate writer identity: {role}/{generation}.")
        else:
            raise CandidateBootstrapError("UNSUPPORTED_MODE")
    except CandidateBootstrapError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 -- redact driver and connection details.
        raise SystemExit(f"CI_CANDIDATE_BOOTSTRAP_FAILED ({type(exc).__name__})") from None


if __name__ == "__main__":
    asyncio.run(main())
