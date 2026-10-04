"""Add bounded database-owned class enrollment operations."""

from alembic import op

revision = "20261003_0026"
down_revision = "20261003_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
    CREATE FUNCTION public.enroll_class_student(p_actor_id integer, p_actor_role text,
        p_classroom_id integer, p_student_user_id integer)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog AS $function$
    DECLARE
        v_actor_role text;
        v_tenant text;
        v_class_tenant text;
        v_student_role text;
        v_student_profile_id integer;
        v_active_tenant text;
        v_inserted integer;
        v_result text;
    BEGIN
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        IF v_actor_role IS DISTINCT FROM 'SCHOOL_ADMIN' OR p_actor_role IS DISTINCT FROM v_actor_role THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        v_tenant := public.resolve_tenant(p_actor_id);
        IF v_tenant IS NULL THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        SELECT tenant_id INTO v_active_tenant FROM public.user_tenant_memberships
         WHERE user_id=p_actor_id AND tenant_id=v_tenant AND status='ACTIVE' AND revoked_at IS NULL
         FOR SHARE;
        IF v_active_tenant IS NULL THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        SELECT tenant_id INTO v_class_tenant FROM public.classrooms WHERE id=p_classroom_id FOR SHARE;
        IF v_class_tenant IS NULL OR v_class_tenant IS DISTINCT FROM v_tenant THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        SELECT role INTO v_student_role FROM public.users WHERE id=p_student_user_id FOR SHARE;
        SELECT id INTO v_student_profile_id FROM public.student_profiles WHERE student_id=p_student_user_id;
        SELECT tenant_id INTO v_active_tenant FROM public.user_tenant_memberships
         WHERE user_id=p_student_user_id AND tenant_id=v_tenant
           AND status='ACTIVE' AND revoked_at IS NULL FOR SHARE;
        IF v_student_role IS DISTINCT FROM 'STUDENT' OR v_student_profile_id IS NULL
           OR v_active_tenant IS NULL THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(
            'class-enrollment:' || p_classroom_id::text || ':' || v_student_profile_id::text, 0));
        INSERT INTO public.class_memberships(classroom_id,student_id)
        VALUES (p_classroom_id,v_student_profile_id)
        ON CONFLICT (classroom_id,student_id) DO NOTHING;
        GET DIAGNOSTICS v_inserted = ROW_COUNT;
        IF v_inserted = 1 THEN
            v_result := 'CREATED';
            INSERT INTO public.audit_logs(actor_user_id,action,resource_type,resource_id,metadata_json)
            VALUES (p_actor_id,'class_member_added','class_membership',p_classroom_id::text,
                jsonb_build_object('actor_user_id',p_actor_id,'tenant_id',v_tenant,
                    'classroom_id',p_classroom_id,'target_user_id',p_student_user_id,
                    'result',v_result,'timestamp',clock_timestamp())::text);
        ELSE
            v_result := 'EXISTING';
        END IF;
        RETURN jsonb_build_object('status',v_result,'classroom_id',p_classroom_id,
            'student_user_id',p_student_user_id,'tenant_id',v_tenant);
    END
    $function$
    """)
    op.execute(r"""
    CREATE FUNCTION public.remove_class_student(p_actor_id integer, p_actor_role text,
        p_classroom_id integer, p_student_user_id integer)
    RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog AS $function$
    DECLARE
        v_actor_role text;
        v_tenant text;
        v_class_tenant text;
        v_student_role text;
        v_student_profile_id integer;
        v_active_tenant text;
        v_deleted integer;
        v_result text;
    BEGIN
        SELECT role INTO v_actor_role FROM public.users WHERE id=p_actor_id FOR SHARE;
        IF v_actor_role IS DISTINCT FROM 'SCHOOL_ADMIN' OR p_actor_role IS DISTINCT FROM v_actor_role THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        v_tenant := public.resolve_tenant(p_actor_id);
        IF v_tenant IS NULL THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        SELECT tenant_id INTO v_active_tenant FROM public.user_tenant_memberships
         WHERE user_id=p_actor_id AND tenant_id=v_tenant AND status='ACTIVE' AND revoked_at IS NULL
         FOR SHARE;
        IF v_active_tenant IS NULL THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        SELECT tenant_id INTO v_class_tenant FROM public.classrooms WHERE id=p_classroom_id FOR SHARE;
        IF v_class_tenant IS NULL OR v_class_tenant IS DISTINCT FROM v_tenant THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        SELECT role INTO v_student_role FROM public.users WHERE id=p_student_user_id FOR SHARE;
        SELECT id INTO v_student_profile_id FROM public.student_profiles WHERE student_id=p_student_user_id;
        SELECT tenant_id INTO v_active_tenant FROM public.user_tenant_memberships
         WHERE user_id=p_student_user_id AND tenant_id=v_tenant
           AND status='ACTIVE' AND revoked_at IS NULL FOR SHARE;
        IF v_student_role IS DISTINCT FROM 'STUDENT' OR v_student_profile_id IS NULL
           OR v_active_tenant IS NULL THEN
            RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='class_enrollment_denied';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(
            'class-enrollment:' || p_classroom_id::text || ':' || v_student_profile_id::text, 0));
        DELETE FROM public.class_memberships
         WHERE classroom_id=p_classroom_id AND student_id=v_student_profile_id;
        GET DIAGNOSTICS v_deleted = ROW_COUNT;
        IF v_deleted = 1 THEN
            v_result := 'REMOVED';
            INSERT INTO public.audit_logs(actor_user_id,action,resource_type,resource_id,metadata_json)
            VALUES (p_actor_id,'class_member_removed','class_membership',p_classroom_id::text,
                jsonb_build_object('actor_user_id',p_actor_id,'tenant_id',v_tenant,
                    'classroom_id',p_classroom_id,'target_user_id',p_student_user_id,
                    'result',v_result,'timestamp',clock_timestamp())::text);
        ELSE
            v_result := 'ALREADY_ABSENT';
        END IF;
        RETURN jsonb_build_object('status',v_result,'classroom_id',p_classroom_id,
            'student_user_id',p_student_user_id,'tenant_id',v_tenant);
    END
    $function$
    """)
    for function in (
        "public.enroll_class_student(integer,text,integer,integer)",
        "public.remove_class_student(integer,text,integer,integer)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC")
    op.execute(r"""
    DO $grant$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime') THEN
            EXECUTE 'REVOKE ALL ON FUNCTION public.enroll_class_student(integer,text,integer,integer) FROM app_runtime';
            EXECUTE 'REVOKE ALL ON FUNCTION public.remove_class_student(integer,text,integer,integer) FROM app_runtime';
            EXECUTE 'GRANT EXECUTE ON FUNCTION public.enroll_class_student(integer,text,integer,integer) TO app_runtime';
            EXECUTE 'GRANT EXECUTE ON FUNCTION public.remove_class_student(integer,text,integer,integer) TO app_runtime';
        END IF;
    END
    $grant$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION public.remove_class_student(integer,text,integer,integer)")
    op.execute("DROP FUNCTION public.enroll_class_student(integer,text,integer,integer)")
