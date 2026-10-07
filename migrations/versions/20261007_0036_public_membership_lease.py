"""Gate MAOS-A12TGI: transaction-bound membership leases for public RLS.

Revision ID: 20261007_0036
Revises: 20261006_0035
"""
from __future__ import annotations

from alembic import op

revision = "20261007_0036"
down_revision = "20261006_0035"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "assignment_snapshots",
    "assignment_statuses",
    "assignment_targets",
    "assignments",
    "classrooms",
    "exam_attempts",
    "exam_results",
    "exams",
    "student_submissions",
    "submission_reviews",
    "submission_revisions",
    "teacher_profiles",
)


OWNER_INVARIANT = """
DO $owner$
DECLARE owner_oid oid;
BEGIN
    SELECT oid INTO owner_oid FROM pg_catalog.pg_roles
     WHERE rolname='tenant_lease_owner'
       AND NOT (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole
                OR rolinherit OR rolreplication OR rolbypassrls);
    IF owner_oid IS NULL THEN
        RAISE EXCEPTION 'tenant_lease_owner missing or unsafe role attributes';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members
               WHERE roleid=owner_oid OR member=owner_oid) THEN
        RAISE EXCEPTION 'tenant_lease_owner has unexpected role memberships';
    END IF;
END
$owner$
"""


def upgrade() -> None:
    op.execute(
        """
        DO $role$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='tenant_lease_owner') THEN
                RAISE EXCEPTION 'tenant_lease_owner already exists; refusing reuse';
            END IF;
            CREATE ROLE tenant_lease_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
        END
        $role$
        """
    )
    op.execute(OWNER_INVARIANT)
    op.execute("GRANT EXECUTE ON FUNCTION public.resolve_tenant(integer) TO tenant_lease_owner")
    op.execute(
        """
        CREATE FUNCTION public.acquire_public_tenant_membership_lease(
            p_user_id integer, p_expected_tenant text
        ) RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        BEGIN
            -- Clear stale or caller-forged context before checking eligibility.
            PERFORM pg_catalog.set_config('app.user_id', '', true);
            PERFORM pg_catalog.set_config('app.tenant_id', '', true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_user_id', '', true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_tenant_id', '', true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_validated_user_id', '', true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_validated_tenant_id', '', true);

            IF pg_catalog.current_setting('transaction_isolation') <> 'read committed'
               OR p_user_id IS NULL OR p_user_id <= 0
               OR p_expected_tenant IS NULL OR p_expected_tenant = '' THEN
                RETURN false;
            END IF;

            -- Shares the exact existing exclusive key used by all canonical
            -- membership writers in migration 20261003_0025.
            PERFORM pg_catalog.pg_advisory_xact_lock_shared(
                pg_catalog.hashtextextended('tenant-membership-user:' || p_user_id::text, 0)
            );
            PERFORM pg_catalog.set_config('app.public_membership_lease_user_id', p_user_id::text, true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_tenant_id', p_expected_tenant, true);
            RETURN true;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.validate_public_tenant_membership_lease(
            p_user_id integer, p_expected_tenant text
        ) RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        DECLARE
            v_resolved_tenant text;
            v_lock_key bigint;
        BEGIN
            -- Every failed validation leaves RLS without an authoritative context.
            PERFORM pg_catalog.set_config('app.user_id', '', true);
            PERFORM pg_catalog.set_config('app.tenant_id', '', true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_validated_user_id', '', true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_validated_tenant_id', '', true);

            IF pg_catalog.current_setting('transaction_isolation') <> 'read committed'
               OR p_user_id IS NULL OR p_user_id <= 0
               OR p_expected_tenant IS NULL OR p_expected_tenant = ''
               OR pg_catalog.current_setting('app.public_membership_lease_user_id', true) IS DISTINCT FROM p_user_id::text
               OR pg_catalog.current_setting('app.public_membership_lease_tenant_id', true) IS DISTINCT FROM p_expected_tenant THEN
                RETURN false;
            END IF;

            v_lock_key := pg_catalog.hashtextextended('tenant-membership-user:' || p_user_id::text, 0);
            IF NOT EXISTS (
                SELECT 1
                  FROM pg_catalog.pg_locks AS l
                 WHERE l.locktype = 'advisory'
                   AND l.database = (SELECT d.oid FROM pg_catalog.pg_database AS d WHERE d.datname = pg_catalog.current_database())
                   AND l.pid = pg_catalog.pg_backend_pid()
                   AND l.granted
                   AND l.mode = 'ShareLock'
                   AND l.objsubid = 1
                   AND ((l.classid::bigint << 32) | l.objid::bigint) = v_lock_key
            ) THEN
                RETURN false;
            END IF;

            -- This resolver call is a separate SQL statement after lease acquisition;
            -- under READ COMMITTED it therefore gets a fresh post-wait snapshot.
            SELECT public.resolve_tenant(p_user_id) INTO v_resolved_tenant;
            IF v_resolved_tenant IS DISTINCT FROM p_expected_tenant THEN
                RETURN false;
            END IF;

            PERFORM pg_catalog.set_config('app.user_id', p_user_id::text, true);
            PERFORM pg_catalog.set_config('app.tenant_id', v_resolved_tenant, true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_validated_user_id', p_user_id::text, true);
            PERFORM pg_catalog.set_config('app.public_membership_lease_validated_tenant_id', v_resolved_tenant, true);
            RETURN true;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.has_public_tenant_membership_lease(p_tenant_id text)
        RETURNS boolean
        LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        DECLARE
            v_user_id integer;
            v_context_user_id integer;
            v_validated_user_id integer;
            v_context_tenant text;
            v_validated_tenant text;
            v_lease_tenant text;
            v_lock_key bigint;
        BEGIN
            IF pg_catalog.current_setting('transaction_isolation') <> 'read committed'
               OR p_tenant_id IS NULL OR p_tenant_id = '' THEN
                RETURN false;
            END IF;

            v_context_tenant := pg_catalog.current_setting('app.tenant_id', true);
            v_lease_tenant := pg_catalog.current_setting('app.public_membership_lease_tenant_id', true);
            v_validated_tenant := pg_catalog.current_setting(
                'app.public_membership_lease_validated_tenant_id', true
            );
            BEGIN
                v_context_user_id := NULLIF(
                    pg_catalog.current_setting('app.user_id', true), ''
                )::integer;
                v_validated_user_id := NULLIF(
                    pg_catalog.current_setting('app.public_membership_lease_validated_user_id', true), ''
                )::integer;
                v_user_id := pg_catalog.current_setting('app.public_membership_lease_user_id', true)::integer;
            EXCEPTION WHEN OTHERS THEN
                RETURN false;
            END;

            IF v_context_user_id IS NULL OR v_context_user_id <= 0
               OR v_validated_user_id IS NULL OR v_validated_user_id <= 0
               OR v_user_id IS NULL OR v_user_id <= 0
               OR v_context_user_id IS DISTINCT FROM v_validated_user_id
               OR v_context_user_id IS DISTINCT FROM v_user_id
               OR v_context_tenant IS NULL OR v_context_tenant = ''
               OR v_lease_tenant IS NULL OR v_lease_tenant = ''
               OR v_validated_tenant IS NULL OR v_validated_tenant = ''
               OR v_context_tenant IS DISTINCT FROM p_tenant_id
               OR v_lease_tenant IS DISTINCT FROM p_tenant_id
               OR v_validated_tenant IS DISTINCT FROM p_tenant_id THEN
                RETURN false;
            END IF;
            v_lock_key := pg_catalog.hashtextextended('tenant-membership-user:' || v_user_id::text, 0);
            RETURN EXISTS (
                SELECT 1
                  FROM pg_catalog.pg_locks AS l
                 WHERE l.locktype = 'advisory'
                   AND l.database = (SELECT d.oid FROM pg_catalog.pg_database AS d WHERE d.datname = pg_catalog.current_database())
                   AND l.pid = pg_catalog.pg_backend_pid()
                   AND l.granted
                   AND l.mode = 'ShareLock'
                   AND l.objsubid = 1
                   AND ((l.classid::bigint << 32) | l.objid::bigint) = v_lock_key
            );
        END
        $function$
        """
    )
    op.execute("ALTER FUNCTION public.acquire_public_tenant_membership_lease(integer,text) OWNER TO tenant_lease_owner")
    op.execute("ALTER FUNCTION public.validate_public_tenant_membership_lease(integer,text) OWNER TO tenant_lease_owner")
    op.execute("ALTER FUNCTION public.has_public_tenant_membership_lease(text) OWNER TO tenant_lease_owner")
    op.execute("REVOKE ALL ON FUNCTION public.acquire_public_tenant_membership_lease(integer,text) FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.validate_public_tenant_membership_lease(integer,text) FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.has_public_tenant_membership_lease(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.acquire_public_tenant_membership_lease(integer,text) TO app_runtime")
    op.execute("GRANT EXECUTE ON FUNCTION public.validate_public_tenant_membership_lease(integer,text) TO app_runtime")
    op.execute("GRANT EXECUTE ON FUNCTION public.has_public_tenant_membership_lease(text) TO app_runtime")
    for table in TENANT_TABLES:
        op.execute(
            f"""
            ALTER POLICY tenant_isolation ON public.{table}
              USING (tenant_id::text = current_setting('app.tenant_id', true)
                     AND public.has_public_tenant_membership_lease(tenant_id::text))
              WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
                          AND public.has_public_tenant_membership_lease(tenant_id::text))
            """
        )


def downgrade() -> None:
    op.execute(OWNER_INVARIANT)
    for table in TENANT_TABLES:
        op.execute(
            f"""
            ALTER POLICY tenant_isolation ON public.{table}
              USING (tenant_id::text = current_setting('app.tenant_id', true))
              WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
            """
        )
    op.execute("DROP FUNCTION public.has_public_tenant_membership_lease(text)")
    op.execute("DROP FUNCTION public.validate_public_tenant_membership_lease(integer,text)")
    op.execute("DROP FUNCTION public.acquire_public_tenant_membership_lease(integer,text)")
    op.execute("REVOKE EXECUTE ON FUNCTION public.resolve_tenant(integer) FROM tenant_lease_owner")
    op.execute("DROP ROLE tenant_lease_owner")
