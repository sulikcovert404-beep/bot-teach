"""Expand submission revision structures and bridge legacy runtime writes."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0028"
down_revision = "20261003_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column("submit_idempotency_key", sa.String(128), nullable=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=True),
        sa.UniqueConstraint("submission_id", "revision_no", name="uq_submission_revision_number"),
        sa.UniqueConstraint("submission_id", "submit_idempotency_key", name="uq_submission_revision_key"),
        sa.UniqueConstraint("id", "submission_id", "tenant_id", name="uq_revision_parent_tenant"),
        sa.ForeignKeyConstraint(
            ["submission_id", "tenant_id"],
            ["student_submissions.id", "student_submissions.tenant_id"],
            name="fk_revision_parent_tenant", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("revision_no > 0", name="ck_revision_positive"),
        sa.CheckConstraint(
            "(provenance = 'BASELINE_BACKFILL' AND submit_idempotency_key IS NULL AND request_fingerprint IS NULL) OR "
            "(provenance = 'LEGACY_COMPAT' AND submit_idempotency_key IS NULL AND request_fingerprint IS NULL) OR "
            "(provenance = 'SUBMITTED' AND submit_idempotency_key IS NOT NULL AND "
            "length(submit_idempotency_key) > 0 AND request_fingerprint IS NOT NULL AND length(request_fingerprint) = 64)",
            name="ck_revision_provenance_key",
        ),
    )
    op.create_index("ix_submission_revisions_tenant_id", "submission_revisions", ["tenant_id"])

    op.add_column("student_submissions", sa.Column("current_revision_id", sa.Integer(), nullable=True))
    op.add_column("submission_reviews", sa.Column("submission_revision_id", sa.Integer(), nullable=True))
    op.add_column("submission_reviews", sa.Column("association_provenance", sa.String(32), nullable=True))

    op.create_foreign_key(
        "fk_submission_current_revision", "student_submissions", "submission_revisions",
        ["current_revision_id", "id", "tenant_id"], ["id", "submission_id", "tenant_id"],
        deferrable=True, initially="DEFERRED", postgresql_not_valid=True,
    )
    op.create_foreign_key(
        "fk_review_revision_owner", "submission_reviews", "submission_revisions",
        ["submission_revision_id", "submission_id", "tenant_id"],
        ["id", "submission_id", "tenant_id"], ondelete="RESTRICT", postgresql_not_valid=True,
    )
    op.create_check_constraint(
        "ck_review_provenance", "submission_reviews",
        "association_provenance IN ('MIGRATION_BASELINE_ONLY', 'EXACT_REVISION', 'LEGACY_COMPAT')",
        postgresql_not_valid=True,
    )
    op.create_check_constraint(
        "ck_review_revision_present", "submission_reviews",
        "submission_revision_id IS NOT NULL AND association_provenance IS NOT NULL",
        postgresql_not_valid=True,
    )

    op.create_table(
        "submission_revision_backfill_state",
        sa.Column("singleton", sa.Boolean(), primary_key=True, server_default=sa.true()),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("last_submission_id", sa.Integer(), nullable=True),
        sa.Column("processed_submissions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("processed_reviews", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("singleton", name="ck_submission_revision_backfill_singleton"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'VALIDATED', 'CONTRACTED')",
            name="ck_submission_revision_backfill_status",
        ),
    )
    op.execute("INSERT INTO public.submission_revision_backfill_state(singleton, status) VALUES (true, 'PENDING')")
    op.create_table(
        "submission_revision_rollout_state",
        sa.Column("singleton", sa.Boolean(), primary_key=True, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.CheckConstraint(
            "status IN ('COMPATIBILITY', 'CONTRACTED')",
            name="ck_submission_revision_rollout_status",
        ),
    )
    op.execute("INSERT INTO public.submission_revision_rollout_state(singleton,status) VALUES (true,'COMPATIBILITY')")
    op.execute("REVOKE ALL ON TABLE public.submission_revision_rollout_state FROM PUBLIC")

    op.execute("""
        CREATE FUNCTION public.gate738e_sync_legacy_submission_revision()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog AS $function$
        DECLARE
            v_revision_id integer;
            v_content text;
            v_rollout_status text;
        BEGIN
            SELECT status INTO v_rollout_status
              FROM public.submission_revision_rollout_state
             WHERE singleton = true FOR SHARE;
            IF v_rollout_status IS NULL OR v_rollout_status NOT IN ('COMPATIBILITY', 'CONTRACTED') THEN
                RAISE EXCEPTION 'submission revision rollout state is unavailable'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.status NOT IN ('SUBMITTED', 'REVIEWED') THEN
                RETURN NEW;
            END IF;

            -- Serialize against backfill at this parent row. If a legacy
            -- writer wins first, preserve its OLD state before adding NEW.
            IF v_rollout_status = 'COMPATIBILITY'
               AND TG_OP = 'UPDATE'
               AND OLD.status IN ('SUBMITTED', 'REVIEWED')
               AND (OLD.revision, OLD.content_json, OLD.submitted_at)
                   IS DISTINCT FROM (NEW.revision, NEW.content_json, NEW.submitted_at) THEN
                SELECT id, content_json INTO v_revision_id, v_content
                  FROM public.submission_revisions
                 WHERE submission_id = OLD.id AND revision_no = OLD.revision;

                IF v_revision_id IS NULL THEN
                    INSERT INTO public.submission_revisions
                        (submission_id, tenant_id, revision_no, content_json, submitted_at, provenance)
                    VALUES
                        (OLD.id, OLD.tenant_id, OLD.revision, OLD.content_json, OLD.submitted_at,
                         'BASELINE_BACKFILL')
                    ON CONFLICT (submission_id, revision_no) DO NOTHING
                    RETURNING id INTO v_revision_id;
                    IF v_revision_id IS NOT NULL THEN
                        v_content := OLD.content_json;
                    ELSE
                        SELECT id, content_json INTO v_revision_id, v_content
                          FROM public.submission_revisions
                         WHERE submission_id = OLD.id AND revision_no = OLD.revision;
                    END IF;
                    IF v_revision_id IS NULL OR v_content IS DISTINCT FROM OLD.content_json THEN
                        RAISE EXCEPTION 'legacy baseline conflicts with immutable snapshot'
                            USING ERRCODE = '23514';
                    END IF;
                ELSIF v_content IS DISTINCT FROM OLD.content_json THEN
                    RAISE EXCEPTION 'legacy baseline conflicts with immutable snapshot'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            SELECT id, content_json INTO v_revision_id, v_content
              FROM public.submission_revisions
             WHERE submission_id = NEW.id AND revision_no = NEW.revision;

            IF v_revision_id IS NULL THEN
                IF v_rollout_status = 'CONTRACTED' THEN
                    RAISE EXCEPTION 'contracted submission write requires a matching immutable revision'
                        USING ERRCODE = '55000';
                END IF;
                INSERT INTO public.submission_revisions
                    (submission_id, tenant_id, revision_no, content_json, submitted_at, provenance)
                VALUES
                    (NEW.id, NEW.tenant_id, NEW.revision, NEW.content_json, NEW.submitted_at, 'LEGACY_COMPAT')
                ON CONFLICT (submission_id, revision_no) DO NOTHING
                RETURNING id INTO v_revision_id;

                IF v_revision_id IS NULL THEN
                    SELECT id, content_json INTO v_revision_id, v_content
                      FROM public.submission_revisions
                     WHERE submission_id = NEW.id AND revision_no = NEW.revision;
                    IF v_content IS DISTINCT FROM NEW.content_json THEN
                        RAISE EXCEPTION 'legacy submission revision conflicts with immutable snapshot';
                    END IF;
                END IF;
            ELSIF v_content IS DISTINCT FROM NEW.content_json THEN
                RAISE EXCEPTION 'legacy submission revision conflicts with immutable snapshot';
            END IF;

            UPDATE public.student_submissions
               SET current_revision_id = v_revision_id
             WHERE id = NEW.id AND current_revision_id IS DISTINCT FROM v_revision_id;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("""
        CREATE FUNCTION public.gate738e_sync_legacy_submission_review()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog AS $function$
        DECLARE
            v_revision_id integer;
            v_rollout_status text;
        BEGIN
            SELECT status INTO v_rollout_status
              FROM public.submission_revision_rollout_state
             WHERE singleton = true FOR SHARE;
            IF v_rollout_status IS NULL OR v_rollout_status NOT IN ('COMPATIBILITY', 'CONTRACTED') THEN
                RAISE EXCEPTION 'submission revision rollout state is unavailable'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.submission_revision_id IS NULL THEN
                IF v_rollout_status = 'CONTRACTED' THEN
                    RAISE EXCEPTION 'contracted review write requires an explicit revision association'
                        USING ERRCODE = '55000';
                END IF;
                SELECT current_revision_id INTO v_revision_id
                  FROM public.student_submissions
                 WHERE id = NEW.submission_id AND tenant_id = NEW.tenant_id;
                IF v_revision_id IS NULL THEN
                    RAISE EXCEPTION 'review cannot be linked to a submission without a current revision';
                END IF;
                NEW.submission_revision_id := v_revision_id;
                NEW.association_provenance := 'LEGACY_COMPAT';
            ELSIF NEW.association_provenance IS NULL THEN
                NEW.association_provenance := 'LEGACY_COMPAT';
            END IF;
            SELECT id INTO v_revision_id
              FROM public.submission_revisions
             WHERE id = NEW.submission_revision_id
               AND submission_id = NEW.submission_id AND tenant_id = NEW.tenant_id;
            IF v_revision_id IS NULL THEN
                RAISE EXCEPTION 'review revision association is invalid'
                    USING ERRCODE = '23503';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("""
        CREATE TRIGGER gate738e_submission_revision_compat
        AFTER INSERT OR UPDATE OF status, revision, content_json, submitted_at
        ON public.student_submissions
        FOR EACH ROW EXECUTE FUNCTION public.gate738e_sync_legacy_submission_revision()
    """)
    op.execute("""
        CREATE TRIGGER gate738e_review_revision_compat
        BEFORE INSERT OR UPDATE ON public.submission_reviews
        FOR EACH ROW EXECUTE FUNCTION public.gate738e_sync_legacy_submission_review()
    """)
    op.execute("ALTER TABLE public.submission_revisions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.submission_revisions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON public.submission_revisions
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
    """)
    op.execute("REVOKE ALL ON TABLE public.submission_revisions FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.gate738e_sync_legacy_submission_revision() FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.gate738e_sync_legacy_submission_review() FROM PUBLIC")
    op.execute("""
        DO $grants$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'app_runtime') THEN
                -- Existing FORCE RLS policies scope these reads and writes.
                -- Parent/review DML is column-scoped; no table-wide DML grant.
                GRANT SELECT ON TABLE public.student_submissions, public.submission_reviews,
                    public.submission_revisions TO app_runtime;
                GRANT INSERT (assignment_id, student_id, tenant_id, status, revision)
                    ON TABLE public.student_submissions TO app_runtime;
                GRANT UPDATE (current_revision_id, revision, content_json, submitted_at, status)
                    ON TABLE public.student_submissions TO app_runtime;
                GRANT INSERT (submission_id, submission_revision_id, tenant_id,
                    association_provenance, review_status, score, teacher_feedback,
                    reviewed_by, reviewed_at)
                    ON TABLE public.submission_reviews TO app_runtime;
                GRANT UPDATE (association_provenance, review_status, score,
                    teacher_feedback, reviewed_by, reviewed_at)
                    ON TABLE public.submission_reviews TO app_runtime;
                GRANT SELECT, INSERT ON TABLE public.submission_revisions TO app_runtime;
                GRANT USAGE ON SEQUENCE public.submission_revisions_id_seq TO app_runtime;
                GRANT USAGE ON SEQUENCE public.student_submissions_id_seq,
                    public.submission_reviews_id_seq TO app_runtime;
            END IF;
        END
        $grants$
    """)

    # Empty databases need no external backfill. Nonempty databases stay gated
    # until the resumable worker records successful validation.
    op.execute("""
        UPDATE public.submission_revision_backfill_state
           SET status = 'VALIDATED', validated_at = pg_catalog.now(), updated_at = pg_catalog.now()
         WHERE singleton = true
           AND NOT EXISTS (
               SELECT 1 FROM public.student_submissions
                WHERE status IN ('SUBMITTED', 'REVIEWED') OR content_json IS NOT NULL
           )
           AND NOT EXISTS (SELECT 1 FROM public.submission_reviews)
    """)


def downgrade() -> None:
    raise RuntimeError("Gate738E expanded submission history is not safely downgradeable")
