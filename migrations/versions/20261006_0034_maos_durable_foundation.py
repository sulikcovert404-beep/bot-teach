"""Create the MAOS V1 durable audit and effect-intent foundation.

This is a persistence-only boundary. It deliberately contains no dispatcher,
provider integration, approval state, or lifecycle authority.
"""

from alembic import op

revision = "20261006_0034"
down_revision = "20261004_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $roles$
        BEGIN
            IF current_setting('server_version_num')::integer < 160000 THEN
                RAISE EXCEPTION 'MAOS A10 requires PostgreSQL 16';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime') THEN
                RAISE EXCEPTION 'app_runtime role is required';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='maos_audit_owner') THEN
                CREATE ROLE maos_audit_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_catalog.pg_roles
                 WHERE rolname='maos_audit_owner'
                   AND (rolcanlogin OR rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication)
            ) THEN
                RAISE EXCEPTION 'maos_audit_owner has unsafe role attributes';
            END IF;
            IF pg_catalog.pg_has_role('app_runtime','maos_audit_owner','MEMBER') THEN
                RAISE EXCEPTION 'app_runtime must not inherit or assume maos_audit_owner';
            END IF;
        END
        $roles$
    """)
    op.execute("GRANT maos_audit_owner TO CURRENT_USER")
    op.execute("CREATE SCHEMA maos AUTHORIZATION maos_audit_owner")
    op.execute("GRANT REFERENCES ON TABLE public.school_tenants, public.users TO maos_audit_owner")
    op.execute("GRANT EXECUTE ON FUNCTION public.resolve_tenant(integer) TO maos_audit_owner")
    # PostgreSQL checks EXECUTE at CREATE TRIGGER time. Keep this grant scoped
    # to the no-login owner and only for the trigger-creation window.
    op.execute("GRANT EXECUTE ON FUNCTION public.gate738k_guard_writer() TO maos_audit_owner")
    op.execute("SET LOCAL ROLE maos_audit_owner")

    op.execute("""
        CREATE TABLE maos.operation_reservations (
            tenant_id varchar(64) NOT NULL REFERENCES public.school_tenants(tenant_id) ON DELETE RESTRICT,
            operation_id uuid NOT NULL,
            operation_digest char(64) NOT NULL CHECK (operation_digest ~ '^[0-9a-f]{64}$'),
            operation_kind varchar(48) NOT NULL CHECK (operation_kind ~ '^[A-Z][A-Z0-9_]{0,47}$'),
            principal_user_id integer NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (tenant_id, operation_id)
        )
    """)
    op.execute("""
        CREATE TABLE maos.audit_stream_heads (
            tenant_id varchar(64) PRIMARY KEY REFERENCES public.school_tenants(tenant_id) ON DELETE RESTRICT,
            last_sequence bigint NOT NULL DEFAULT 0 CHECK (last_sequence >= 0),
            last_hash char(64) NOT NULL DEFAULT repeat('0', 64) CHECK (last_hash ~ '^[0-9a-f]{64}$'),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("""
        CREATE TABLE maos.audit_events (
            event_id uuid PRIMARY KEY,
            tenant_id varchar(64) NOT NULL REFERENCES public.school_tenants(tenant_id) ON DELETE RESTRICT,
            sequence bigint NOT NULL CHECK (sequence > 0),
            actor_user_id integer NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
            action_code varchar(48) NOT NULL CHECK (action_code ~ '^[A-Z][A-Z0-9_]{0,47}$'),
            resource_type varchar(48) NOT NULL CHECK (resource_type ~ '^[a-z][a-z0-9_]{0,47}$'),
            resource_id varchar(128) NOT NULL CHECK (length(resource_id) BETWEEN 1 AND 128),
            metadata_digest char(64) NOT NULL CHECK (metadata_digest ~ '^[0-9a-f]{64}$'),
            correlation_id uuid NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            previous_hash char(64) NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
            event_hash char(64) NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
            UNIQUE (tenant_id, sequence),
            UNIQUE (tenant_id, event_id)
        )
    """)
    op.execute("""
        CREATE TABLE maos.effect_intents (
            intent_id uuid PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            operation_id uuid NOT NULL,
            audit_event_id uuid NOT NULL,
            effect_kind varchar(48) NOT NULL CHECK (effect_kind ~ '^[A-Z][A-Z0-9_]{0,47}$'),
            risk_class varchar(16) NOT NULL CHECK (risk_class IN ('LOW','MEDIUM','HIGH')),
            provider_code varchar(48) NOT NULL CHECK (provider_code ~ '^[A-Z][A-Z0-9_]{0,47}$'),
            provider_idempotency_key char(64) NOT NULL CHECK (provider_idempotency_key ~ '^[0-9a-f]{64}$'),
            request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            FOREIGN KEY (tenant_id, operation_id)
                REFERENCES maos.operation_reservations(tenant_id, operation_id) ON DELETE RESTRICT,
            FOREIGN KEY (tenant_id, audit_event_id)
                REFERENCES maos.audit_events(tenant_id, event_id) ON DELETE RESTRICT,
            UNIQUE (tenant_id, operation_id),
            UNIQUE (tenant_id, provider_code, provider_idempotency_key),
            UNIQUE (tenant_id, intent_id)
        )
    """)
    op.execute("""
        CREATE TABLE maos.effect_state_projections (
            tenant_id varchar(64) NOT NULL,
            intent_id uuid NOT NULL,
            state varchar(16) NOT NULL CHECK (state IN ('PREPARED','DISPATCHING','SUCCEEDED','FAILED','UNKNOWN')),
            last_sequence bigint NOT NULL CHECK (last_sequence > 0),
            last_hash char(64) NOT NULL CHECK (last_hash ~ '^[0-9a-f]{64}$'),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (tenant_id, intent_id),
            FOREIGN KEY (tenant_id, intent_id)
                REFERENCES maos.effect_intents(tenant_id, intent_id) ON DELETE RESTRICT
        )
    """)
    op.execute("""
        CREATE TABLE maos.effect_events (
            event_id uuid PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            intent_id uuid NOT NULL,
            sequence bigint NOT NULL CHECK (sequence > 0),
            state varchar(16) NOT NULL CHECK (state IN ('PREPARED','DISPATCHING','SUCCEEDED','FAILED','UNKNOWN')),
            outcome_code varchar(48) NOT NULL CHECK (outcome_code IN (
                'INTENT_CREATED','DISPATCH_MARKED','PRE_DISPATCH_FAILED','PROVIDER_ACCEPTED',
                'PROVIDER_REJECTED','OUTCOME_UNKNOWN','RECONCILED_ACCEPTED','RECONCILED_REJECTED'
            )),
            evidence_digest char(64) NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            previous_hash char(64) NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
            event_hash char(64) NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
            FOREIGN KEY (tenant_id, intent_id)
                REFERENCES maos.effect_intents(tenant_id, intent_id) ON DELETE RESTRICT,
            UNIQUE (tenant_id, intent_id, sequence)
        )
    """)

    op.execute("""
        CREATE FUNCTION maos.current_tenant() RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE p_user integer; p_claim text; p_resolved text;
        BEGIN
            p_user := nullif(current_setting('maos.principal_user_id', true), '')::integer;
            p_claim := nullif(current_setting('maos.tenant_id', true), '');
            IF p_user IS NULL OR p_claim IS NULL THEN RETURN NULL; END IF;
            SELECT public.resolve_tenant(p_user) INTO p_resolved;
            IF p_resolved IS DISTINCT FROM p_claim THEN RETURN NULL; END IF;
            RETURN p_resolved;
        EXCEPTION WHEN invalid_text_representation THEN RETURN NULL;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos.set_principal_context(p_user_id integer) RETURNS text
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE v_tenant text;
        BEGIN
            SELECT public.resolve_tenant(p_user_id) INTO v_tenant;
            IF v_tenant IS NULL THEN RAISE EXCEPTION 'principal has no unique active tenant' USING ERRCODE='42501'; END IF;
            PERFORM pg_catalog.set_config('maos.principal_user_id', p_user_id::text, true);
            PERFORM pg_catalog.set_config('maos.tenant_id', v_tenant, true);
            RETURN v_tenant;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos.reserve_operation(
            p_operation_id uuid, p_digest text, p_kind text, p_principal_user_id integer
        ) RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE v_tenant text; v_user integer; v_existing text; v_existing_kind text;
        BEGIN
            v_tenant := maos.current_tenant();
            v_user := nullif(current_setting('maos.principal_user_id', true), '')::integer;
            IF v_tenant IS NULL OR v_user IS DISTINCT FROM p_principal_user_id THEN
                RAISE EXCEPTION 'tenant/principal context denied' USING ERRCODE='42501';
            END IF;
            IF p_digest !~ '^[0-9a-f]{64}$' OR p_kind !~ '^[A-Z][A-Z0-9_]{0,47}$' THEN
                RAISE EXCEPTION 'invalid operation contract' USING ERRCODE='22023';
            END IF;
            INSERT INTO maos.operation_reservations(tenant_id,operation_id,operation_digest,operation_kind,principal_user_id)
            VALUES(v_tenant,p_operation_id,p_digest,p_kind,p_principal_user_id)
            ON CONFLICT (tenant_id,operation_id) DO NOTHING;
            IF FOUND THEN RETURN true; END IF;
            SELECT operation_digest,operation_kind INTO v_existing,v_existing_kind FROM maos.operation_reservations
             WHERE tenant_id=v_tenant AND operation_id=p_operation_id FOR SHARE;
            IF v_existing IS DISTINCT FROM p_digest OR v_existing_kind IS DISTINCT FROM p_kind THEN
                RAISE EXCEPTION 'idempotency key conflicts with reserved digest' USING ERRCODE='23505';
            END IF;
            RETURN false;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos.append_audit_event(
            p_event_id uuid, p_action text, p_resource_type text, p_resource_id text,
            p_metadata_digest text, p_correlation_id uuid
        ) RETURNS bigint
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE v_tenant text; v_user integer; v_seq bigint; v_prev text; v_hash text;
        BEGIN
            v_tenant := maos.current_tenant();
            v_user := nullif(current_setting('maos.principal_user_id', true), '')::integer;
            IF v_tenant IS NULL OR v_user IS NULL THEN RAISE EXCEPTION 'tenant/principal context denied' USING ERRCODE='42501'; END IF;
            INSERT INTO maos.audit_stream_heads(tenant_id) VALUES(v_tenant) ON CONFLICT DO NOTHING;
            SELECT last_sequence,last_hash INTO v_seq,v_prev FROM maos.audit_stream_heads WHERE tenant_id=v_tenant FOR UPDATE;
            v_seq := v_seq + 1;
            v_hash := encode(sha256(convert_to(jsonb_build_array(v_prev,v_tenant,v_seq,p_event_id,
                v_user,p_action,p_resource_type,p_resource_id,p_metadata_digest,p_correlation_id)::text, 'UTF8')), 'hex');
            INSERT INTO maos.audit_events(event_id,tenant_id,sequence,actor_user_id,action_code,
                resource_type,resource_id,metadata_digest,correlation_id,previous_hash,event_hash)
            VALUES(p_event_id,v_tenant,v_seq,v_user,p_action,p_resource_type,p_resource_id,
                p_metadata_digest,p_correlation_id,v_prev,v_hash);
            UPDATE maos.audit_stream_heads SET last_sequence=v_seq,last_hash=v_hash,updated_at=clock_timestamp()
             WHERE tenant_id=v_tenant;
            RETURN v_seq;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos.prepare_effect(
            p_intent_id uuid, p_operation_id uuid, p_audit_event_id uuid, p_effect_kind text,
            p_risk text, p_provider text, p_request_digest text, p_evidence_digest text
        ) RETURNS uuid
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE v_tenant text; v_key text; v_hash text; v_zero text := repeat('0',64);
        BEGIN
            v_tenant := maos.current_tenant();
            IF v_tenant IS NULL THEN RAISE EXCEPTION 'tenant context denied' USING ERRCODE='42501'; END IF;
            IF p_risk='CRITICAL' OR p_request_digest !~ '^[0-9a-f]{64}$' OR p_evidence_digest !~ '^[0-9a-f]{64}$' THEN
                RAISE EXCEPTION 'effect contract rejected' USING ERRCODE='22023';
            END IF;
            v_key := encode(sha256(convert_to(v_tenant || ':' || p_operation_id::text, 'UTF8')), 'hex');
            INSERT INTO maos.effect_intents(intent_id,tenant_id,operation_id,audit_event_id,effect_kind,
                risk_class,provider_code,provider_idempotency_key,request_digest)
            VALUES(p_intent_id,v_tenant,p_operation_id,p_audit_event_id,p_effect_kind,p_risk,p_provider,v_key,p_request_digest);
            v_hash := encode(sha256(convert_to(jsonb_build_array(v_zero,v_tenant,p_intent_id,1,'PREPARED',
                'INTENT_CREATED',p_evidence_digest)::text, 'UTF8')), 'hex');
            INSERT INTO maos.effect_events(event_id,tenant_id,intent_id,sequence,state,outcome_code,
                evidence_digest,previous_hash,event_hash)
            VALUES(gen_random_uuid(),v_tenant,p_intent_id,1,'PREPARED','INTENT_CREATED',p_evidence_digest,v_zero,v_hash);
            INSERT INTO maos.effect_state_projections(tenant_id,intent_id,state,last_sequence,last_hash)
            VALUES(v_tenant,p_intent_id,'PREPARED',1,v_hash);
            RETURN p_intent_id;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos.record_effect_outcome(
            p_intent_id uuid,p_next_state text,p_outcome text,p_evidence_digest text
        ) RETURNS bigint
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE v_tenant text; v_old text; v_seq bigint; v_prev text; v_hash text;
        BEGIN
            v_tenant := maos.current_tenant();
            IF v_tenant IS NULL THEN RAISE EXCEPTION 'tenant context denied' USING ERRCODE='42501'; END IF;
            SELECT state,last_sequence,last_hash INTO v_old,v_seq,v_prev
              FROM maos.effect_state_projections WHERE tenant_id=v_tenant AND intent_id=p_intent_id FOR UPDATE;
            IF NOT FOUND THEN RAISE EXCEPTION 'effect intent missing' USING ERRCODE='P0002'; END IF;
            IF NOT ((v_old='PREPARED' AND p_next_state IN ('DISPATCHING','FAILED')) OR
                    (v_old='DISPATCHING' AND p_next_state IN ('SUCCEEDED','FAILED','UNKNOWN')) OR
                    (v_old='UNKNOWN' AND p_next_state IN ('SUCCEEDED','FAILED'))) THEN
                RAISE EXCEPTION 'illegal effect state transition' USING ERRCODE='55000';
            END IF;
            IF NOT ((v_old='PREPARED' AND p_next_state='DISPATCHING' AND p_outcome='DISPATCH_MARKED') OR
                    (v_old='PREPARED' AND p_next_state='FAILED' AND p_outcome='PRE_DISPATCH_FAILED') OR
                    (v_old='DISPATCHING' AND p_next_state='SUCCEEDED' AND p_outcome='PROVIDER_ACCEPTED') OR
                    (v_old='DISPATCHING' AND p_next_state='FAILED' AND p_outcome='PROVIDER_REJECTED') OR
                    (v_old='DISPATCHING' AND p_next_state='UNKNOWN' AND p_outcome='OUTCOME_UNKNOWN') OR
                    (v_old='UNKNOWN' AND p_next_state='SUCCEEDED' AND p_outcome='RECONCILED_ACCEPTED') OR
                    (v_old='UNKNOWN' AND p_next_state='FAILED' AND p_outcome='RECONCILED_REJECTED')) THEN
                RAISE EXCEPTION 'effect outcome does not match state transition' USING ERRCODE='22023';
            END IF;
            IF p_evidence_digest !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'invalid evidence digest' USING ERRCODE='22023'; END IF;
            v_seq := v_seq + 1;
            v_hash := encode(sha256(convert_to(jsonb_build_array(v_prev,v_tenant,p_intent_id,v_seq,
                p_next_state,p_outcome,p_evidence_digest)::text, 'UTF8')), 'hex');
            INSERT INTO maos.effect_events(event_id,tenant_id,intent_id,sequence,state,outcome_code,
                evidence_digest,previous_hash,event_hash)
            VALUES(gen_random_uuid(),v_tenant,p_intent_id,v_seq,p_next_state,p_outcome,p_evidence_digest,v_prev,v_hash);
            UPDATE maos.effect_state_projections SET state=p_next_state,last_sequence=v_seq,
                last_hash=v_hash,updated_at=clock_timestamp() WHERE tenant_id=v_tenant AND intent_id=p_intent_id;
            RETURN v_seq;
        END
        $fn$
    """)

    op.execute("""
        CREATE FUNCTION maos.reject_immutable_change() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$ BEGIN RAISE EXCEPTION 'MAOS authoritative records are append-only' USING ERRCODE='55000'; END $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos.reject_truncate() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$ BEGIN RAISE EXCEPTION 'MAOS records cannot be truncated' USING ERRCODE='55000'; END $fn$
    """)
    op.execute("""
        DO $policy$
        DECLARE t text;
        BEGIN
            FOREACH t IN ARRAY ARRAY['operation_reservations','audit_stream_heads','audit_events',
                'effect_intents','effect_state_projections','effect_events'] LOOP
                EXECUTE pg_catalog.format('ALTER TABLE maos.%I ENABLE ROW LEVEL SECURITY', t);
                EXECUTE pg_catalog.format('ALTER TABLE maos.%I FORCE ROW LEVEL SECURITY', t);
                EXECUTE pg_catalog.format('CREATE POLICY tenant_isolation ON maos.%I USING (tenant_id = maos.current_tenant()) WITH CHECK (tenant_id = maos.current_tenant())', t);
                EXECUTE pg_catalog.format('CREATE TRIGGER gate738k_writer_fence BEFORE INSERT OR UPDATE OR DELETE ON maos.%I FOR EACH ROW EXECUTE FUNCTION public.gate738k_guard_writer()', t);
                EXECUTE pg_catalog.format('CREATE TRIGGER reject_truncate BEFORE TRUNCATE ON maos.%I FOR EACH STATEMENT EXECUTE FUNCTION maos.reject_truncate()', t);
            END LOOP;
            FOREACH t IN ARRAY ARRAY['operation_reservations','audit_events','effect_intents','effect_events'] LOOP
                EXECUTE pg_catalog.format('CREATE TRIGGER reject_mutation BEFORE UPDATE OR DELETE ON maos.%I FOR EACH ROW EXECUTE FUNCTION maos.reject_immutable_change()', t);
            END LOOP;
        END
        $policy$
    """)
    op.execute("REVOKE ALL ON SCHEMA maos FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA maos TO app_runtime")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA maos FROM PUBLIC, app_runtime")
    op.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA maos FROM PUBLIC")
    op.execute("""
        GRANT EXECUTE ON FUNCTION maos.current_tenant(), maos.set_principal_context(integer),
            maos.reserve_operation(uuid,text,text,integer),
            maos.append_audit_event(uuid,text,text,text,text,uuid),
            maos.prepare_effect(uuid,uuid,uuid,text,text,text,text,text),
            maos.record_effect_outcome(uuid,text,text,text) TO app_runtime
    """)
    op.execute("REVOKE ALL ON FUNCTION maos.reject_immutable_change(), maos.reject_truncate() FROM PUBLIC, app_runtime")
    op.execute("RESET ROLE")
    op.execute("REVOKE EXECUTE ON FUNCTION public.gate738k_guard_writer() FROM maos_audit_owner")
    op.execute("REVOKE maos_audit_owner FROM CURRENT_USER")


def downgrade() -> None:
    raise RuntimeError("MAOS durable audit/effect persistence is forward-only; use an approved replacement gate")
