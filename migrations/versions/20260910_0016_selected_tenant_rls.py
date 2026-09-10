"""Add fail-closed tenant RLS policies to selected tenant-owned tables.

This revision is qualified on disposable PostgreSQL first.  Application code must
set ``app.tenant_id`` transaction-locally before enabling it in a live runtime.
"""
from alembic import op

revision = "20260910_0016"
down_revision = "20260909_0015"
branch_labels = None
depends_on = None

TABLES = (
    "assignment_snapshots",
    "assignment_statuses",
    "assignment_targets",
    "assignments",
    "classrooms",
    "content_generation_jobs",
    "student_submissions",
    "submission_reviews",
    "teacher_profiles",
)


def upgrade() -> None:
    for table in TABLES:
        quoted = table.replace('"', '""')
        op.execute(f'ALTER TABLE "{quoted}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{quoted}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'''CREATE POLICY tenant_isolation ON "{quoted}"
                USING (tenant_id = current_setting('app.tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.tenant_id', true))'''
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        quoted = table.replace('"', '""')
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{quoted}"')
        op.execute(f'ALTER TABLE "{quoted}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{quoted}" DISABLE ROW LEVEL SECURITY')
