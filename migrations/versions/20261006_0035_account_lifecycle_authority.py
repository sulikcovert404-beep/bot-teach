"""Add append-only principal lifecycle authority and rebuildable projection."""

from alembic import op

revision = "20261006_0035"
down_revision = "20261006_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $roles$
        BEGIN
            IF current_setting('server_version_num')::integer < 160000 THEN
                RAISE EXCEPTION 'MAOS A11 requires PostgreSQL 16';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime') THEN
                RAISE EXCEPTION 'app_runtime role is required';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='maos_lifecycle_owner') THEN
                CREATE ROLE maos_lifecycle_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='maos_lifecycle_writer') THEN
                CREATE ROLE maos_lifecycle_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_catalog.pg_roles
                 WHERE rolname IN ('maos_lifecycle_owner','maos_lifecycle_writer')
                   AND (rolcanlogin OR rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication)
            ) THEN
                RAISE EXCEPTION 'MAOS lifecycle roles have unsafe role attributes';
            END IF;
            IF pg_catalog.pg_has_role('app_runtime','maos_lifecycle_owner','MEMBER')
               OR pg_catalog.pg_has_role('app_runtime','maos_lifecycle_writer','MEMBER') THEN
                RAISE EXCEPTION 'app_runtime must not inherit lifecycle ownership or writer capability';
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM pg_catalog.pg_auth_members m
                  JOIN pg_catalog.pg_roles granted ON granted.oid=m.roleid
                  JOIN pg_catalog.pg_roles member ON member.oid=m.member
                 WHERE granted.rolname='maos_lifecycle_writer' AND member.rolcanlogin
            ) THEN
                RAISE EXCEPTION 'operational LOGIN role already has lifecycle writer membership';
            END IF;
        END
        $roles$
    """)
    op.execute("GRANT maos_lifecycle_owner TO CURRENT_USER")
    op.execute("GRANT EXECUTE ON FUNCTION public.gate738k_guard_writer() TO maos_lifecycle_owner")
    op.execute("CREATE SCHEMA maos_lifecycle AUTHORIZATION maos_lifecycle_owner")
    op.execute("SET LOCAL ROLE maos_lifecycle_owner")
    op.execute("""
        CREATE TABLE maos_lifecycle.events (
            event_id uuid PRIMARY KEY,
            principal_ref varchar(256) NOT NULL CHECK (length(btrim(principal_ref)) BETWEEN 1 AND 256),
            sequence bigint NOT NULL CHECK (sequence > 0),
            actor_principal_ref varchar(256) NOT NULL CHECK (length(btrim(actor_principal_ref)) BETWEEN 1 AND 256),
            from_state varchar(16) NOT NULL CHECK (from_state IN ('UNRECONCILED','ACTIVE','SUSPENDED','DISABLED')),
            to_state varchar(16) NOT NULL CHECK (to_state IN ('ACTIVE','SUSPENDED','DISABLED')),
            reason_ref varchar(256) NOT NULL CHECK (length(btrim(reason_ref)) BETWEEN 1 AND 256),
            authority_ref varchar(256) NOT NULL CHECK (length(btrim(authority_ref)) BETWEEN 1 AND 256),
            evidence_digest char(64) NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
            audit_event_ref varchar(256) NOT NULL CHECK (length(btrim(audit_event_ref)) BETWEEN 1 AND 256),
            occurred_at timestamptz NOT NULL,
            previous_hash char(64) NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
            event_hash char(64) NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
            UNIQUE (principal_ref, sequence),
            CHECK (from_state <> to_state)
        )
    """)
    op.execute("""
        CREATE TABLE maos_lifecycle.current_state_projection (
            principal_ref varchar(256) PRIMARY KEY
                CHECK (length(btrim(principal_ref)) BETWEEN 1 AND 256),
            state varchar(16) NOT NULL CHECK (state IN ('ACTIVE','SUSPENDED','DISABLED')),
            last_sequence bigint NOT NULL CHECK (last_sequence > 0),
            last_hash char(64) NOT NULL CHECK (last_hash ~ '^[0-9a-f]{64}$'),
            rebuilt_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("""
        CREATE FUNCTION maos_lifecycle.reject_immutable_change() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$ BEGIN RAISE EXCEPTION 'MAOS lifecycle events are append-only' USING ERRCODE='55000'; END $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos_lifecycle.reject_truncate() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$ BEGIN RAISE EXCEPTION 'MAOS lifecycle events cannot be truncated' USING ERRCODE='55000'; END $fn$
    """)
    op.execute("""
        CREATE TRIGGER lifecycle_writer_fence
        BEFORE INSERT OR UPDATE OR DELETE ON maos_lifecycle.events
        FOR EACH ROW EXECUTE FUNCTION public.gate738k_guard_writer()
    """)
    op.execute("""
        CREATE TRIGGER lifecycle_projection_writer_fence
        BEFORE INSERT OR UPDATE OR DELETE ON maos_lifecycle.current_state_projection
        FOR EACH ROW EXECUTE FUNCTION public.gate738k_guard_writer()
    """)
    op.execute("""
        CREATE TRIGGER lifecycle_events_immutable
        BEFORE UPDATE OR DELETE ON maos_lifecycle.events
        FOR EACH ROW EXECUTE FUNCTION maos_lifecycle.reject_immutable_change()
    """)
    op.execute("""
        CREATE TRIGGER lifecycle_events_no_truncate
        BEFORE TRUNCATE ON maos_lifecycle.events
        FOR EACH STATEMENT EXECUTE FUNCTION maos_lifecycle.reject_truncate()
    """)
    op.execute("""
        CREATE FUNCTION maos_lifecycle.resolve_state_internal(p_principal_ref text,p_verify_projection boolean)
        RETURNS text
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE
            e record;
            v_expected_sequence bigint := 1;
            v_expected_state text := 'UNRECONCILED';
            v_previous_hash text := repeat('0',64);
            v_computed_hash text;
            v_last_state text;
            v_last_hash text;
            v_last_sequence bigint := 0;
            v_previous_at timestamptz;
            v_projection record;
        BEGIN
            IF p_principal_ref IS NULL OR length(btrim(p_principal_ref)) NOT BETWEEN 1 AND 256 THEN
                RAISE EXCEPTION 'invalid lifecycle principal reference' USING ERRCODE='22023';
            END IF;
            FOR e IN
                SELECT event_id, principal_ref, sequence, actor_principal_ref, from_state, to_state,
                       reason_ref, authority_ref, evidence_digest, audit_event_ref, occurred_at,
                       previous_hash, event_hash
                  FROM maos_lifecycle.events
                 WHERE principal_ref=p_principal_ref
                 ORDER BY sequence
            LOOP
                IF e.sequence <> v_expected_sequence OR e.from_state <> v_expected_state
                   OR e.previous_hash <> v_previous_hash THEN
                    RAISE EXCEPTION 'lifecycle event history is unanchored or discontinuous' USING ERRCODE='55000';
                END IF;
                IF v_previous_at IS NOT NULL AND e.occurred_at < v_previous_at THEN
                    RAISE EXCEPTION 'lifecycle event time moved backwards' USING ERRCODE='55000';
                END IF;
                IF NOT ((e.from_state='UNRECONCILED' AND e.to_state IN ('ACTIVE','SUSPENDED','DISABLED'))
                     OR (e.from_state='ACTIVE' AND e.to_state IN ('SUSPENDED','DISABLED'))
                     OR (e.from_state='SUSPENDED' AND e.to_state IN ('ACTIVE','DISABLED'))) THEN
                    RAISE EXCEPTION 'invalid or terminal lifecycle transition' USING ERRCODE='55000';
                END IF;
                v_computed_hash := pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
                    pg_catalog.jsonb_build_array(
                        v_previous_hash,e.event_id,e.principal_ref,e.sequence,e.actor_principal_ref,
                        e.from_state,e.to_state,e.reason_ref,e.authority_ref,e.evidence_digest,
                        e.audit_event_ref,(extract(epoch FROM e.occurred_at)*1000000)::bigint
                    )::text,'UTF8')),'hex');
                IF e.event_hash <> v_computed_hash THEN
                    RAISE EXCEPTION 'lifecycle event hash mismatch' USING ERRCODE='55000';
                END IF;
                v_expected_sequence := v_expected_sequence + 1;
                v_expected_state := e.to_state;
                v_previous_hash := e.event_hash;
                v_last_sequence := e.sequence;
                v_last_state := e.to_state;
                v_last_hash := e.event_hash;
                v_previous_at := e.occurred_at;
            END LOOP;
            IF p_verify_projection THEN
                SELECT state,last_sequence,last_hash INTO v_projection
                  FROM maos_lifecycle.current_state_projection
                 WHERE principal_ref=p_principal_ref;
            END IF;
            IF v_last_sequence=0 THEN
                IF p_verify_projection AND FOUND THEN
                    RAISE EXCEPTION 'orphan lifecycle projection' USING ERRCODE='55000';
                END IF;
                RETURN 'UNRECONCILED';
            END IF;
            IF p_verify_projection AND (NOT FOUND OR v_projection.state IS DISTINCT FROM v_last_state
               OR v_projection.last_sequence IS DISTINCT FROM v_last_sequence
               OR v_projection.last_hash IS DISTINCT FROM v_last_hash) THEN
                RAISE EXCEPTION 'lifecycle projection is missing or inconsistent' USING ERRCODE='55000';
            END IF;
            RETURN v_last_state;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos_lifecycle.resolve_state(p_principal_ref text) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$ SELECT maos_lifecycle.resolve_state_internal(p_principal_ref,true) $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos_lifecycle.append_event(
            p_event_id uuid, p_principal_ref text, p_actor_principal_ref text,
            p_from_state text, p_to_state text, p_reason_ref text, p_authority_ref text,
            p_evidence_digest text, p_audit_event_ref text, p_occurred_at timestamptz
        ) RETURNS bigint
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE
            v_state text;
            v_sequence bigint;
            v_previous_hash text := repeat('0',64);
            v_hash text;
            v_existing maos_lifecycle.events%ROWTYPE;
            v_last_occurred_at timestamptz;
        BEGIN
            IF p_event_id IS NULL OR p_principal_ref IS NULL OR length(btrim(p_principal_ref)) NOT BETWEEN 1 AND 256
               OR p_actor_principal_ref IS NULL OR length(btrim(p_actor_principal_ref)) NOT BETWEEN 1 AND 256
               OR p_reason_ref IS NULL OR length(btrim(p_reason_ref)) NOT BETWEEN 1 AND 256
               OR p_authority_ref IS NULL OR length(btrim(p_authority_ref)) NOT BETWEEN 1 AND 256
               OR p_audit_event_ref IS NULL OR length(btrim(p_audit_event_ref)) NOT BETWEEN 1 AND 256
               OR p_evidence_digest !~ '^[0-9a-f]{64}$' OR p_occurred_at IS NULL THEN
                RAISE EXCEPTION 'invalid lifecycle event contract' USING ERRCODE='22023';
            END IF;
            PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_principal_ref,0));
            SELECT * INTO v_existing FROM maos_lifecycle.events WHERE event_id=p_event_id;
            IF FOUND THEN
                IF v_existing.principal_ref IS DISTINCT FROM p_principal_ref
                   OR v_existing.actor_principal_ref IS DISTINCT FROM p_actor_principal_ref
                   OR v_existing.from_state IS DISTINCT FROM p_from_state
                   OR v_existing.to_state IS DISTINCT FROM p_to_state
                   OR v_existing.reason_ref IS DISTINCT FROM p_reason_ref
                   OR v_existing.authority_ref IS DISTINCT FROM p_authority_ref
                   OR v_existing.evidence_digest IS DISTINCT FROM p_evidence_digest
                   OR v_existing.audit_event_ref IS DISTINCT FROM p_audit_event_ref
                   OR v_existing.occurred_at IS DISTINCT FROM p_occurred_at THEN
                    RAISE EXCEPTION 'lifecycle event id conflicts with existing content' USING ERRCODE='23505';
                END IF;
                PERFORM maos_lifecycle.resolve_state(p_principal_ref);
                RETURN v_existing.sequence;
            END IF;
            v_state := maos_lifecycle.resolve_state(p_principal_ref);
            IF p_from_state IS DISTINCT FROM v_state THEN
                RAISE EXCEPTION 'lifecycle event does not continue current state' USING ERRCODE='55000';
            END IF;
            IF NOT ((p_from_state='UNRECONCILED' AND p_to_state IN ('ACTIVE','SUSPENDED','DISABLED'))
                 OR (p_from_state='ACTIVE' AND p_to_state IN ('SUSPENDED','DISABLED'))
                 OR (p_from_state='SUSPENDED' AND p_to_state IN ('ACTIVE','DISABLED'))) THEN
                RAISE EXCEPTION 'invalid or terminal lifecycle transition' USING ERRCODE='55000';
            END IF;
            SELECT coalesce(max(sequence),0)+1 INTO v_sequence
              FROM maos_lifecycle.events WHERE principal_ref=p_principal_ref;
            SELECT event_hash,occurred_at INTO v_previous_hash,v_last_occurred_at FROM maos_lifecycle.events
             WHERE principal_ref=p_principal_ref ORDER BY sequence DESC LIMIT 1;
            v_previous_hash := coalesce(v_previous_hash,repeat('0',64));
            IF v_last_occurred_at IS NOT NULL AND p_occurred_at < v_last_occurred_at THEN
                RAISE EXCEPTION 'lifecycle event time cannot move backwards' USING ERRCODE='55000';
            END IF;
            v_hash := pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
                pg_catalog.jsonb_build_array(
                    v_previous_hash,p_event_id,p_principal_ref,v_sequence,p_actor_principal_ref,
                    p_from_state,p_to_state,p_reason_ref,p_authority_ref,p_evidence_digest,
                    p_audit_event_ref,(extract(epoch FROM p_occurred_at)*1000000)::bigint
                )::text,'UTF8')),'hex');
            INSERT INTO maos_lifecycle.events(
                event_id,principal_ref,sequence,actor_principal_ref,from_state,to_state,reason_ref,
                authority_ref,evidence_digest,audit_event_ref,occurred_at,previous_hash,event_hash
            ) VALUES (
                p_event_id,p_principal_ref,v_sequence,p_actor_principal_ref,p_from_state,p_to_state,
                p_reason_ref,p_authority_ref,p_evidence_digest,p_audit_event_ref,p_occurred_at,
                v_previous_hash,v_hash
            );
            INSERT INTO maos_lifecycle.current_state_projection(principal_ref,state,last_sequence,last_hash)
            VALUES(p_principal_ref,p_to_state,v_sequence,v_hash)
            ON CONFLICT (principal_ref) DO UPDATE SET state=excluded.state,
                last_sequence=excluded.last_sequence,last_hash=excluded.last_hash,rebuilt_at=clock_timestamp();
            RETURN v_sequence;
        END
        $fn$
    """)
    op.execute("""
        CREATE FUNCTION maos_lifecycle.rebuild_projection() RETURNS bigint
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
        AS $fn$
        DECLARE p record; v_count bigint := 0; v_state text; v_last record;
        BEGIN
            DELETE FROM maos_lifecycle.current_state_projection;
            FOR p IN SELECT DISTINCT principal_ref FROM maos_lifecycle.events ORDER BY principal_ref LOOP
                v_state := maos_lifecycle.resolve_state_internal(p.principal_ref,false);
                SELECT sequence,event_hash INTO v_last FROM maos_lifecycle.events
                 WHERE principal_ref=p.principal_ref ORDER BY sequence DESC LIMIT 1;
                INSERT INTO maos_lifecycle.current_state_projection(principal_ref,state,last_sequence,last_hash)
                VALUES(p.principal_ref,v_state,v_last.sequence,v_last.event_hash);
                v_count := v_count + 1;
            END LOOP;
            RETURN v_count;
        END
        $fn$
    """)
    op.execute("RESET ROLE")
    op.execute("REVOKE ALL ON SCHEMA maos_lifecycle FROM PUBLIC, app_runtime")
    op.execute("GRANT USAGE ON SCHEMA maos_lifecycle TO maos_lifecycle_writer")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA maos_lifecycle FROM PUBLIC, app_runtime, maos_lifecycle_writer")
    op.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA maos_lifecycle FROM PUBLIC, app_runtime, maos_lifecycle_writer")
    op.execute("REVOKE ALL ON FUNCTION maos_lifecycle.resolve_state_internal(text,boolean) FROM PUBLIC, app_runtime, maos_lifecycle_writer")
    op.execute("GRANT EXECUTE ON FUNCTION maos_lifecycle.resolve_state(text) TO maos_lifecycle_writer")
    op.execute("GRANT EXECUTE ON FUNCTION maos_lifecycle.append_event(uuid,text,text,text,text,text,text,text,text,timestamptz) TO maos_lifecycle_writer")
    op.execute("GRANT EXECUTE ON FUNCTION maos_lifecycle.rebuild_projection() TO maos_lifecycle_owner")
    op.execute("REVOKE EXECUTE ON FUNCTION public.gate738k_guard_writer() FROM maos_lifecycle_owner")
    op.execute("REVOKE maos_lifecycle_owner FROM CURRENT_USER")


def downgrade() -> None:
    raise RuntimeError("MAOS lifecycle authority is forward-only; use an approved replacement gate")
