"""Fail-closed database preconditions for the submission contract revisions.

This module deliberately inspects only generation identifiers, application
names, transaction timestamps, and role/catalog metadata. It never reads SQL
text, request payloads, or user data.
"""

from __future__ import annotations

import os
import re

import sqlalchemy as sa

_GENERATION = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(f"Gate738P contract guard refused: {reason}")


def assert_contract_preconditions(bind) -> dict[str, str | int]:
    """Lock legacy admission and verify every database-checkable precondition.

    Candidate HTTP health is a separate runtime prerequisite and must be
    checked by the staged rollout runner before invoking the final contract
    target. This function checks only durable database facts.
    """
    _require(bind.dialect.name == "postgresql", "PostgreSQL is required")
    candidate = os.environ.get("WRITER_GENERATION", "").strip()
    candidate_role = os.environ.get("WRITER_DATABASE_ROLE", "").strip()
    _require(bool(_GENERATION.fullmatch(candidate)) and candidate != "legacy",
             "WRITER_GENERATION must identify the candidate release")
    _require(bool(re.fullmatch(r"[A-Za-z0-9._-]{1,63}", candidate_role))
             and candidate_role != "app_runtime",
             "WRITER_DATABASE_ROLE must identify a distinct candidate login role")
    _require(bind.scalar(sa.text("SELECT current_user <> 'app_runtime'")) is True,
             "contract requires the release/migration identity")

    stats_visible = bind.scalar(sa.text("""
        SELECT r.rolsuper OR pg_catalog.pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')
          FROM pg_catalog.pg_roles AS r
         WHERE r.rolname = current_user
    """))
    _require(stats_visible is True, "migration identity cannot completely observe pg_stat_activity")

    runtime = bind.execute(sa.text("""
        SELECT oid, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb, rolreplication
          FROM pg_catalog.pg_roles
         WHERE rolname = 'app_runtime'
    """)).mappings().first()
    _require(runtime is not None, "app_runtime role is missing")
    _require(not any(runtime[key] for key in (
        "rolsuper", "rolbypassrls", "rolcreaterole", "rolcreatedb", "rolreplication"
    )), "app_runtime has elevated role attributes")
    _require(not bind.scalar(sa.text("""
        SELECT pg_catalog.has_table_privilege(
            'app_runtime', 'public.ai_teacher_writer_generation_state', 'UPDATE'
        )
    """)), "app_runtime can mutate writer-generation state")
    _require(bind.scalar(sa.text("""
        SELECT pg_catalog.has_table_privilege(
            'app_runtime', 'public.alembic_version', 'SELECT'
        )
    """)) is True, "app_runtime cannot perform read-only migration readiness")
    _require(bind.scalar(sa.text("""
        SELECT pg_catalog.has_function_privilege(
            'app_runtime', 'public.gate738k_admit_writer()', 'EXECUTE'
        )
    """)) is True, "app_runtime cannot use the writer admission boundary")
    public_execute = bind.scalar(sa.text("""
        SELECT EXISTS (
            SELECT 1
              FROM pg_catalog.pg_proc AS p
              JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
              CROSS JOIN LATERAL pg_catalog.aclexplode(
                  COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))
              ) AS acl
             WHERE n.nspname = 'public'
               AND p.proname = 'gate738k_admit_writer'
               AND pg_catalog.pg_get_function_identity_arguments(p.oid) = ''
               AND acl.grantee = 0
               AND acl.privilege_type = 'EXECUTE'
        )
    """))
    _require(not public_execute, "writer admission function is executable by PUBLIC")

    # Hold an exclusive row lock until this migration transaction commits.
    # Already-admitted legacy transactions retain FOR SHARE through completion;
    # subsequent/queued legacy admissions resume only after the durable FENCED
    # state is committed and will be rejected by Gate738K.
    legacy_state = bind.scalar(sa.text("""
        SELECT state
          FROM public.ai_teacher_writer_generation_state
         WHERE generation = 'legacy' AND database_role = 'app_runtime'
         FOR UPDATE
    """))
    _require(legacy_state == "FENCED", "legacy generation is not FENCED")

    candidate_state = bind.scalar(sa.text("""
        SELECT state
          FROM public.ai_teacher_writer_generation_state
         WHERE generation = :generation AND database_role = :database_role
         FOR SHARE
    """), {"generation": candidate, "database_role": candidate_role})
    _require(candidate_state == "SERVING", "candidate generation is missing or not SERVING")

    other_admissible_generations = bind.scalar(sa.text("""
        SELECT count(*)
          FROM public.ai_teacher_writer_generation_state
         WHERE state IN ('SERVING', 'DRAINING')
           AND generation <> :candidate
    """), {"candidate": candidate})
    _require(other_admissible_generations == 0,
             "another writer generation remains SERVING or DRAINING")

    old_transactions = bind.scalar(sa.text("""
        SELECT count(*)
          FROM pg_catalog.pg_stat_activity AS activity
          JOIN public.ai_teacher_writer_generation_state AS generation
            ON generation.database_role = activity.usename
         WHERE activity.datname = pg_catalog.current_database()
           AND activity.pid <> pg_catalog.pg_backend_pid()
           AND generation.generation = 'legacy'
           AND activity.xact_start IS NOT NULL
    """))
    _require(old_transactions == 0, "an OLD-generation database transaction remains active")

    candidate_sessions = bind.scalar(sa.text("""
        SELECT count(*)
          FROM pg_catalog.pg_stat_activity
         WHERE datname = pg_catalog.current_database()
           AND usename = :database_role
           AND pid <> pg_catalog.pg_backend_pid()
    """), {"database_role": candidate_role})
    _require(candidate_sessions > 0, "no live database session exists for the healthy candidate role")

    unknown_runtime_sessions = bind.scalar(sa.text("""
        SELECT count(*)
          FROM pg_catalog.pg_stat_activity AS activity
          JOIN public.ai_teacher_writer_generation_state AS generation
            ON generation.database_role = activity.usename
         WHERE activity.datname = pg_catalog.current_database()
           AND activity.pid <> pg_catalog.pg_backend_pid()
           AND generation.generation <> :candidate
           AND generation.state IN ('SERVING', 'DRAINING')
    """), {"candidate": candidate})
    _require(unknown_runtime_sessions == 0,
             "an OLD or non-candidate admission-capable database session remains")

    return {
        "legacy_state": legacy_state,
        "candidate_state": candidate_state,
        "candidate_database_role": candidate_role,
        "other_admissible_generations": other_admissible_generations,
        "old_generation_transactions": old_transactions,
        "unknown_runtime_sessions": unknown_runtime_sessions,
    }
