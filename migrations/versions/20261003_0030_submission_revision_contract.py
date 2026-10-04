"""Validate the online backfill and apply the small final revision contract."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0030"
down_revision = "20261004_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from migrations.gate738p_contract_guard import assert_contract_preconditions

    assert_contract_preconditions(bind)
    status = bind.scalar(sa.text("""
        SELECT status FROM public.submission_revision_backfill_state
         WHERE singleton = true
    """))
    if status != "VALIDATED":
        raise RuntimeError("Gate738E backfill must be validated before contract; DO NOT CONTRACT")

    op.create_check_constraint(
        "ck_submission_current_revision", "student_submissions",
        "(status = 'NOT_SUBMITTED' AND current_revision_id IS NULL) OR "
        "(status IN ('SUBMITTED', 'REVIEWED') AND current_revision_id IS NOT NULL)",
        postgresql_not_valid=True,
    )
    op.create_check_constraint(
        "ck_review_revision_id_not_null", "submission_reviews",
        "submission_revision_id IS NOT NULL", postgresql_not_valid=True,
    )
    op.create_check_constraint(
        "ck_review_association_provenance_not_null", "submission_reviews",
        "association_provenance IS NOT NULL", postgresql_not_valid=True,
    )
    op.execute("ALTER TABLE public.student_submissions VALIDATE CONSTRAINT fk_submission_current_revision")
    op.execute("ALTER TABLE public.submission_reviews VALIDATE CONSTRAINT fk_review_revision_owner")
    op.execute("ALTER TABLE public.student_submissions VALIDATE CONSTRAINT ck_submission_current_revision")
    op.execute("ALTER TABLE public.submission_reviews VALIDATE CONSTRAINT ck_review_provenance")
    op.execute("ALTER TABLE public.submission_reviews VALIDATE CONSTRAINT ck_review_revision_present")
    op.execute("ALTER TABLE public.submission_reviews VALIDATE CONSTRAINT ck_review_revision_id_not_null")
    op.execute("ALTER TABLE public.submission_reviews VALIDATE CONSTRAINT ck_review_association_provenance_not_null")

    # 0029 built this unique index concurrently. Keep it as an index instead
    # of attaching it as a table constraint: attaching requests an
    # ACCESS EXCLUSIVE lock but adds no integrity beyond the valid unique index.
    op.drop_constraint(
        "uq_submission_reviews_submission", "submission_reviews", type_="unique"
    )

    op.execute("""
        CREATE FUNCTION public.gate738e_submission_revision_immutable()
        RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $function$
        BEGIN
            RAISE EXCEPTION 'submission revision rows are immutable'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("""
        CREATE TRIGGER submission_revision_immutable
        BEFORE UPDATE OR DELETE ON public.submission_revisions
        FOR EACH ROW EXECUTE FUNCTION public.gate738e_submission_revision_immutable()
    """)
    op.execute("REVOKE ALL ON FUNCTION public.gate738e_submission_revision_immutable() FROM PUBLIC")
    op.execute("""
        UPDATE public.submission_revision_backfill_state
           SET status = 'CONTRACTED', updated_at = pg_catalog.now()
         WHERE singleton = true
    """)


def downgrade() -> None:
    raise RuntimeError("Submission history contract cannot be destructively downgraded")
