"""Finalize the selected-table RLS contract after the canonical 0017 revision.

The policy DDL is intentionally owned by 0016.  This revision closes the
lineage after the Lesson Pack revision without re-parenting or re-running the
policy DDL.  ``content_generation_jobs`` remains explicitly excluded from
Phase 1 because its nullable tenant semantics are unresolved.
"""
from alembic import op

revision = "20260910_0018"
down_revision = "20260910_0017"
branch_labels = None
depends_on = None

TABLES = (
    "assignment_snapshots",
    "assignment_statuses",
    "assignment_targets",
    "assignments",
    "classrooms",
    "student_submissions",
    "submission_reviews",
    "teacher_profiles",
)


def upgrade() -> None:
    # Verify the selected-table contract without repeating policy DDL.
    for table in TABLES:
        op.execute(
            f"""DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class c
                WHERE c.relname = '{table}' AND c.relrowsecurity
            ) THEN RAISE EXCEPTION 'RLS contract missing for {table}'; END IF;
            END $$;"""
        )


def downgrade() -> None:
    # Policy ownership remains with 0016; this lineage marker has no destructive
    # downgrade side effects.
    pass
