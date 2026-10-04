"""Add narrowly scoped DB-owned membership lifecycle operations."""

from alembic import op

revision = "20261003_0025"
down_revision = "20261003_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
    CREATE FUNCTION public.bootstrap_school_tenant(
        p_actor_id integer, p_actor_role text, p_payload jsonb,
        p_fingerprint text, p_idempotency_key text, p_correlation_id text
    ) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog AS $function$
    DECLARE
        v_claim public.provisioning_idempotency_keys%ROWTYPE;
        v_actor_role text;
        v_admin_role text;
        v_tenant text := p_payload->>'tenant_id';
        v_admin_id integer := (p_payload->>'school_admin_user_id')::integer;
        v_membership_id integer;
        v_result jsonb;
    BEGIN
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        SELECT role INTO v_admin_role FROM public.users WHERE id=v_admin_id FOR SHARE;
        IF v_actor_role IS DISTINCT FROM 'SUPER_ADMIN' OR p_actor_role IS DISTINCT FROM v_actor_role
           OR v_admin_role IS DISTINCT FROM 'SCHOOL_ADMIN' THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-bootstrap-id:' || v_tenant, 0));
        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-membership-idempotency:TENANT_BOOTSTRAP:' || p_idempotency_key, 0));
        SELECT * INTO v_claim FROM public.provisioning_idempotency_keys
         WHERE operation='TENANT_BOOTSTRAP' AND idempotency_key=p_idempotency_key FOR UPDATE;
        IF FOUND THEN
            IF v_claim.actor_user_id <> p_actor_id OR v_claim.request_fingerprint <> p_fingerprint THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_idempotency_conflict';
            END IF;
            IF v_claim.status='SUCCEEDED' THEN RETURN jsonb_set(v_claim.response_json::jsonb,'{status}','"REPLAY"'::jsonb); END IF;
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
        END IF;
        INSERT INTO public.provisioning_idempotency_keys
            (operation,idempotency_key,request_fingerprint,status,actor_user_id,correlation_id)
        VALUES ('TENANT_BOOTSTRAP',p_idempotency_key,p_fingerprint,'CLAIMED',p_actor_id,p_correlation_id)
        RETURNING * INTO v_claim;

        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-membership-user:' || v_admin_id::text, 0));
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        SELECT role INTO v_admin_role FROM public.users WHERE id=v_admin_id FOR SHARE;
        IF v_actor_role IS DISTINCT FROM 'SUPER_ADMIN' OR p_actor_role IS DISTINCT FROM v_actor_role
           OR v_admin_role IS DISTINCT FROM 'SCHOOL_ADMIN'
           OR v_tenant IS NULL OR length(v_tenant) NOT BETWEEN 1 AND 64
           OR p_payload->>'school_name' IS NULL OR length(p_payload->>'school_name') NOT BETWEEN 1 AND 150
           OR coalesce(length(p_payload->>'region'),0) > 100 THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        IF EXISTS (SELECT 1 FROM public.school_tenants WHERE tenant_id=v_tenant)
           OR EXISTS (SELECT 1 FROM public.user_tenant_memberships
                       WHERE user_id=v_admin_id AND status='ACTIVE' AND revoked_at IS NULL) THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
        END IF;
        INSERT INTO public.school_tenants
            (tenant_id,school_name,region,max_student_quota,max_teacher_quota,licensing_status,data_isolation_verified)
        VALUES (v_tenant,p_payload->>'school_name',coalesce(p_payload->>'region',''),500,25,'PILOT_ACTIVE',true);
        INSERT INTO public.user_tenant_memberships(user_id,tenant_id,status,created_by)
        VALUES (v_admin_id,v_tenant,'ACTIVE',p_actor_id) RETURNING id INTO v_membership_id;
        INSERT INTO public.audit_logs(actor_user_id,action,resource_type,resource_id,metadata_json)
        VALUES (p_actor_id,'TENANT_BOOTSTRAPPED','tenant_membership',v_admin_id::text,
            jsonb_build_object('target_user_id',v_admin_id,'tenant_id',v_tenant,'result','CREATED','correlation_id',p_correlation_id)::text);
        v_result := jsonb_build_object('status','CREATED','user_id',v_admin_id,'tenant_id',v_tenant,'membership_id',v_membership_id);
        UPDATE public.provisioning_idempotency_keys SET status='SUCCEEDED',user_id=v_admin_id,
            response_json=v_result::text,completed_at=now() WHERE id=v_claim.id;
        RETURN v_result;
    END
    $function$;
    """)
    op.execute(r"""
    CREATE FUNCTION public.provision_tenant_membership(
        p_actor_id integer, p_actor_role text, p_payload jsonb,
        p_fingerprint text, p_idempotency_key text, p_correlation_id text
    ) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog AS $function$
    DECLARE
        v_claim public.provisioning_idempotency_keys%ROWTYPE;
        v_actor_role text;
        v_actor_membership_id integer;
        v_target_role text;
        v_target_id integer := (p_payload->>'user_id')::integer;
        v_tenant text := p_payload->>'tenant_id';
        v_requested_role text := p_payload->>'role';
        v_membership public.user_tenant_memberships%ROWTYPE;
        v_membership_id integer;
        v_other text;
        v_result jsonb;
    BEGIN
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        IF v_actor_role IS NULL OR v_actor_role IS DISTINCT FROM p_actor_role
           OR v_actor_role NOT IN ('SUPER_ADMIN','SCHOOL_ADMIN') THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        IF v_actor_role='SCHOOL_ADMIN' THEN
            SELECT id INTO v_actor_membership_id FROM public.user_tenant_memberships
             WHERE user_id=p_actor_id AND tenant_id=v_tenant AND status='ACTIVE' AND revoked_at IS NULL
             FOR SHARE;
            IF v_actor_membership_id IS NULL THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
            END IF;
        END IF;
        SELECT role INTO v_target_role FROM public.users WHERE id=v_target_id FOR SHARE;
        IF v_target_role IS NULL OR v_target_role IS DISTINCT FROM v_requested_role
           OR v_requested_role NOT IN ('STUDENT','TEACHER','SCHOOL_ADMIN') THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-membership-idempotency:TENANT_MEMBERSHIP_PROVISION:' || p_idempotency_key, 0));
        SELECT * INTO v_claim FROM public.provisioning_idempotency_keys
         WHERE operation='TENANT_MEMBERSHIP_PROVISION' AND idempotency_key=p_idempotency_key FOR UPDATE;
        IF FOUND THEN
            IF v_claim.actor_user_id <> p_actor_id OR v_claim.request_fingerprint <> p_fingerprint THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_idempotency_conflict';
            END IF;
            IF v_claim.status='SUCCEEDED' THEN RETURN jsonb_set(v_claim.response_json::jsonb,'{status}','"REPLAY"'::jsonb); END IF;
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
        END IF;
        INSERT INTO public.provisioning_idempotency_keys
            (operation,idempotency_key,request_fingerprint,status,actor_user_id,correlation_id)
        VALUES ('TENANT_MEMBERSHIP_PROVISION',p_idempotency_key,p_fingerprint,'CLAIMED',p_actor_id,p_correlation_id)
        RETURNING * INTO v_claim;
        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-membership-user:' || v_target_id::text, 0));
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        SELECT role INTO v_target_role FROM public.users WHERE id=v_target_id FOR SHARE;
        IF v_actor_role IS NULL OR v_actor_role IS DISTINCT FROM p_actor_role
           OR v_target_role IS NULL OR v_target_role IS DISTINCT FROM v_requested_role
           OR v_tenant IS NULL OR v_requested_role NOT IN ('STUDENT','TEACHER','SCHOOL_ADMIN') THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM public.school_tenants WHERE tenant_id=v_tenant) THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_not_found';
        END IF;
        IF v_actor_role='SCHOOL_ADMIN' THEN
            IF v_requested_role NOT IN ('STUDENT','TEACHER') OR NOT EXISTS (
                SELECT 1 FROM public.user_tenant_memberships
                 WHERE user_id=p_actor_id AND tenant_id=v_tenant AND status='ACTIVE' AND revoked_at IS NULL
            ) THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied'; END IF;
        ELSIF v_actor_role <> 'SUPER_ADMIN' THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        SELECT tenant_id INTO v_other FROM public.user_tenant_memberships
         WHERE user_id=v_target_id AND status='ACTIVE' AND revoked_at IS NULL LIMIT 1;
        IF v_other IS NOT NULL AND v_other <> v_tenant THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
        END IF;
        SELECT * INTO v_membership FROM public.user_tenant_memberships
         WHERE user_id=v_target_id AND tenant_id=v_tenant FOR UPDATE;
        IF FOUND THEN
            IF v_membership.status <> 'ACTIVE' OR v_membership.revoked_at IS NOT NULL THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
            END IF;
            v_result := jsonb_build_object('status','EXISTING','user_id',v_target_id,'tenant_id',v_tenant,'membership_id',v_membership.id);
        ELSE
            INSERT INTO public.user_tenant_memberships(user_id,tenant_id,status,created_by)
            VALUES (v_target_id,v_tenant,'ACTIVE',p_actor_id) RETURNING id INTO v_membership_id;
            v_result := jsonb_build_object('status','CREATED','user_id',v_target_id,'tenant_id',v_tenant,'membership_id',v_membership_id);
            INSERT INTO public.audit_logs(actor_user_id,action,resource_type,resource_id,metadata_json)
            VALUES (p_actor_id,'TENANT_MEMBERSHIP_PROVISIONED','tenant_membership',v_target_id::text,
                jsonb_build_object('target_user_id',v_target_id,'tenant_id',v_tenant,'role',v_requested_role,'result','CREATED','correlation_id',p_correlation_id)::text);
        END IF;
        UPDATE public.provisioning_idempotency_keys SET status='SUCCEEDED',user_id=v_target_id,
            response_json=v_result::text,completed_at=now() WHERE id=v_claim.id;
        RETURN v_result;
    END
    $function$;
    """)
    op.execute(r"""
    CREATE FUNCTION public.revoke_tenant_membership(
        p_actor_id integer, p_actor_role text, p_payload jsonb,
        p_fingerprint text, p_idempotency_key text, p_correlation_id text
    ) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog AS $function$
    DECLARE
        v_claim public.provisioning_idempotency_keys%ROWTYPE;
        v_actor_role text;
        v_target_role text;
        v_actor_membership_id integer;
        v_target_id integer := (p_payload->>'user_id')::integer;
        v_tenant text := p_payload->>'tenant_id';
        v_member public.user_tenant_memberships%ROWTYPE;
        v_result jsonb;
    BEGIN
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        SELECT role INTO v_target_role FROM public.users WHERE id=v_target_id FOR SHARE;
        IF v_actor_role IS DISTINCT FROM p_actor_role OR v_actor_role NOT IN ('SUPER_ADMIN','SCHOOL_ADMIN') THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        IF v_actor_role='SCHOOL_ADMIN' AND (
            v_target_role IS NULL OR v_target_role NOT IN ('STUDENT','TEACHER')
        ) THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied'; END IF;
        IF v_actor_role='SCHOOL_ADMIN' THEN
            SELECT id INTO v_actor_membership_id FROM public.user_tenant_memberships
             WHERE user_id=p_actor_id AND tenant_id=v_tenant AND status='ACTIVE' AND revoked_at IS NULL
             FOR SHARE;
            IF v_actor_membership_id IS NULL THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
            END IF;
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-membership-idempotency:TENANT_MEMBERSHIP_REVOKE:' || p_idempotency_key, 0));
        SELECT * INTO v_claim FROM public.provisioning_idempotency_keys
         WHERE operation='TENANT_MEMBERSHIP_REVOKE' AND idempotency_key=p_idempotency_key FOR UPDATE;
        IF FOUND THEN
            IF v_claim.actor_user_id <> p_actor_id OR v_claim.request_fingerprint <> p_fingerprint THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_idempotency_conflict';
            END IF;
            IF v_claim.status='SUCCEEDED' THEN RETURN jsonb_set(v_claim.response_json::jsonb,'{status}','"REPLAY"'::jsonb); END IF;
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
        END IF;
        INSERT INTO public.provisioning_idempotency_keys
            (operation,idempotency_key,request_fingerprint,status,actor_user_id,correlation_id)
        VALUES ('TENANT_MEMBERSHIP_REVOKE',p_idempotency_key,p_fingerprint,'CLAIMED',p_actor_id,p_correlation_id)
        RETURNING * INTO v_claim;
        PERFORM pg_advisory_xact_lock(hashtextextended('tenant-membership-user:' || v_target_id::text, 0));
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        IF v_actor_role IS DISTINCT FROM p_actor_role OR v_actor_role NOT IN ('SUPER_ADMIN','SCHOOL_ADMIN') THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        IF v_actor_role='SCHOOL_ADMIN' AND NOT EXISTS (
            SELECT 1 FROM public.user_tenant_memberships
             WHERE user_id=p_actor_id AND tenant_id=v_tenant AND status='ACTIVE' AND revoked_at IS NULL
        ) THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied'; END IF;
        SELECT * INTO v_member FROM public.user_tenant_memberships
         WHERE user_id=v_target_id AND tenant_id=v_tenant FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_not_found'; END IF;
        IF v_member.status='SUSPENDED' THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict'; END IF;
        IF v_member.status='ACTIVE' THEN
            IF (SELECT role FROM public.users WHERE id=v_target_id)='SCHOOL_ADMIN'
               AND NOT EXISTS (SELECT 1 FROM public.user_tenant_memberships m
                   JOIN public.users u ON u.id=m.user_id
                   WHERE m.tenant_id=v_tenant AND m.status='ACTIVE' AND m.revoked_at IS NULL
                     AND u.role='SCHOOL_ADMIN' AND m.user_id<>v_target_id) THEN
                RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_conflict';
            END IF;
            UPDATE public.user_tenant_memberships SET status='REVOKED',revoked_at=now()
             WHERE id=v_member.id;
            INSERT INTO public.audit_logs(actor_user_id,action,resource_type,resource_id,metadata_json)
            VALUES (p_actor_id,'TENANT_MEMBERSHIP_REVOKED','tenant_membership',v_target_id::text,
                jsonb_build_object('target_user_id',v_target_id,'tenant_id',v_tenant,'result','REVOKED','correlation_id',p_correlation_id)::text);
        END IF;
        v_result := jsonb_build_object('status','REVOKED','user_id',v_target_id,'tenant_id',v_tenant,'membership_id',v_member.id);
        UPDATE public.provisioning_idempotency_keys SET status='SUCCEEDED',user_id=v_target_id,
            response_json=v_result::text,completed_at=now() WHERE id=v_claim.id;
        RETURN v_result;
    END
    $function$;
    """)
    op.execute(r"""
    CREATE FUNCTION public.get_tenant_membership(
        p_actor_id integer, p_actor_role text, p_user_id integer, p_tenant_id text
    ) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path = pg_catalog AS $function$
    DECLARE v_actor_role text; v_member public.user_tenant_memberships%ROWTYPE;
    BEGIN
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id;
        IF v_actor_role IS DISTINCT FROM p_actor_role OR v_actor_role NOT IN ('SUPER_ADMIN','SCHOOL_ADMIN')
           OR (v_actor_role='SCHOOL_ADMIN' AND NOT EXISTS (SELECT 1 FROM public.user_tenant_memberships
               WHERE user_id=p_actor_id AND tenant_id=p_tenant_id AND status='ACTIVE' AND revoked_at IS NULL)) THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_denied';
        END IF;
        SELECT * INTO v_member FROM public.user_tenant_memberships
         WHERE user_id=p_user_id AND tenant_id=p_tenant_id;
        IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='tenant_membership_not_found'; END IF;
        RETURN jsonb_build_object('status',v_member.status,'user_id',v_member.user_id,
            'tenant_id',v_member.tenant_id,'membership_id',v_member.id,'created_at',v_member.created_at,
            'revoked_at',v_member.revoked_at);
    END
    $function$;
    """)
    op.execute("REVOKE ALL ON FUNCTION public.bootstrap_school_tenant(integer,text,jsonb,text,text,text) FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.provision_tenant_membership(integer,text,jsonb,text,text,text) FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.revoke_tenant_membership(integer,text,jsonb,text,text,text) FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.get_tenant_membership(integer,text,integer,text) FROM PUBLIC")
    op.execute(r"""
    DO $grant$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime') THEN
            GRANT EXECUTE ON FUNCTION public.bootstrap_school_tenant(integer,text,jsonb,text,text,text) TO app_runtime;
            GRANT EXECUTE ON FUNCTION public.provision_tenant_membership(integer,text,jsonb,text,text,text) TO app_runtime;
            GRANT EXECUTE ON FUNCTION public.revoke_tenant_membership(integer,text,jsonb,text,text,text) TO app_runtime;
            GRANT EXECUTE ON FUNCTION public.get_tenant_membership(integer,text,integer,text) TO app_runtime;
        END IF;
    END
    $grant$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION public.get_tenant_membership(integer,text,integer,text)")
    op.execute("DROP FUNCTION public.revoke_tenant_membership(integer,text,jsonb,text,text,text)")
    op.execute("DROP FUNCTION public.provision_tenant_membership(integer,text,jsonb,text,text,text)")
    op.execute("DROP FUNCTION public.bootstrap_school_tenant(integer,text,jsonb,text,text,text)")
