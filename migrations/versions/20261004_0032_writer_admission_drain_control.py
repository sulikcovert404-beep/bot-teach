"""Install a persistent database-owned writer-generation fence.

The database row lock is held through every admitted transaction. A control
plane transition therefore waits for already admitted writers and prevents a
queued or restarted process from writing once the new state commits.
"""

import os
import re

import sqlalchemy as sa
from alembic import op

revision = "20261004_0032"
down_revision = "20261003_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_teacher_writer_generation_state",
        sa.Column("generation", sa.String(40), primary_key=True),
        sa.Column("database_role", sa.String(63), nullable=False, unique=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("generation ~ '^[A-Za-z0-9._-]{1,40}$'", name="ck_ai_writer_generation_id"),
        sa.CheckConstraint("state IN ('SERVING', 'DRAINING', 'FENCED')", name="ck_ai_writer_generation_state"),
    )
    bind = op.get_bind()
    legacy_role = bind.scalar(sa.text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime'"))
    if legacy_role is None:
        raise RuntimeError("app_runtime legacy database role is missing")
    bind.execute(sa.text("""
        INSERT INTO public.ai_teacher_writer_generation_state(generation,database_role,state)
        VALUES ('legacy','app_runtime','SERVING')
    """))
    candidate_generation = os.environ.get("WRITER_GENERATION", "").strip()
    candidate_role = os.environ.get("WRITER_DATABASE_ROLE", "").strip()
    if (not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", candidate_generation)
            or candidate_generation == "legacy"):
        raise RuntimeError("WRITER_GENERATION must identify a distinct candidate release")
    if (not re.fullmatch(r"[A-Za-z0-9._-]{1,63}", candidate_role)
            or candidate_role == "app_runtime"):
        raise RuntimeError("WRITER_DATABASE_ROLE must identify a distinct candidate login role")
    role_metadata = bind.execute(sa.text(
        "SELECT rolcanlogin FROM pg_catalog.pg_roles WHERE rolname=:role"
    ), {"role": candidate_role}).mappings().first()
    if role_metadata is None or not role_metadata["rolcanlogin"]:
        raise RuntimeError("candidate PostgreSQL login role is missing")
    legacy_can_assume_candidate = bind.scalar(sa.text(
        "SELECT pg_catalog.pg_has_role('app_runtime', :role, 'MEMBER')"
    ), {"role": candidate_role})
    if legacy_can_assume_candidate:
        raise RuntimeError("app_runtime can assume the candidate PostgreSQL role")
    bind.execute(sa.text("""
        INSERT INTO public.ai_teacher_writer_generation_state(generation,database_role,state)
        VALUES (:generation,:role,'SERVING')
    """), {"generation": candidate_generation, "role": candidate_role})
    op.execute("REVOKE ALL ON TABLE public.ai_teacher_writer_generation_state FROM PUBLIC")

    op.execute("""
        CREATE FUNCTION public.gate738k_admit_writer()
        RETURNS text
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        DECLARE
            v_generation text;
            v_state text;
        BEGIN
            SELECT generation, state INTO v_generation, v_state
              FROM public.ai_teacher_writer_generation_state
             WHERE database_role = session_user
             FOR SHARE;
            IF v_generation IS NULL THEN
                RAISE EXCEPTION 'database role is not registered for writer admission' USING ERRCODE = '42501';
            END IF;
            IF v_state IS DISTINCT FROM 'SERVING' THEN
                RAISE EXCEPTION 'writer generation is not serving' USING ERRCODE = '55000';
            END IF;
            RETURN v_state;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.gate738k_admit_writer() FROM PUBLIC")
    op.execute("""
        DO $grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'app_runtime') THEN
                GRANT EXECUTE ON FUNCTION public.gate738k_admit_writer() TO app_runtime;
                -- Read-only readiness uses this singleton to report migration
                -- drift; runtime receives no write privilege on it.
                GRANT SELECT ON TABLE public.alembic_version TO app_runtime;
            END IF;
        END
        $grant$
    """)

    op.execute("""
        CREATE FUNCTION public.gate738k_guard_writer()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        BEGIN
            -- The admission identity is derived from PostgreSQL session_user,
            -- never from caller-controlled GUCs or application_name.
            PERFORM public.gate738k_admit_writer();
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.gate738k_guard_writer() FROM PUBLIC")
    op.execute("""
        DO $triggers$
        DECLARE
            v_table record;
        BEGIN
            FOR v_table IN
                SELECT c.relname
                  FROM pg_catalog.pg_class c
                  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname = 'public'
                   AND c.relkind IN ('r', 'p')
                   AND c.relname NOT IN (
                       'alembic_version',
                       'ai_teacher_writer_generation_state',
                       'submission_revision_backfill_state',
                       'submission_revision_rollout_state'
                   )
            LOOP
                EXECUTE pg_catalog.format(
                    'CREATE TRIGGER gate738k_writer_fence BEFORE INSERT OR UPDATE OR DELETE ON public.%I '
                    'FOR EACH ROW EXECUTE FUNCTION public.gate738k_guard_writer()',
                    v_table.relname
                );
            END LOOP;
        END
        $triggers$
    """)


def downgrade() -> None:
    raise RuntimeError("Gate738K writer fence is forward-only; use an approved replacement control plane")
