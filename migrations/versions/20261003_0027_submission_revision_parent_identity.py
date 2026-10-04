"""Prepare the parent identity key needed for tenant-safe revision FKs.

The concurrent index is isolated in its own revision so no new columns are
visible without the legacy synchronization hooks that arrive in the next
revision.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0027"
down_revision = "20261003_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_student_submissions_id_tenant_gate738e "
            "ON public.student_submissions (id, tenant_id)"
        )

    index = bind.execute(sa.text("""
        SELECT i.indisunique, i.indisvalid,
               pg_catalog.pg_get_indexdef(i.indexrelid) AS definition
          FROM pg_catalog.pg_index AS i
          JOIN pg_catalog.pg_class AS c ON c.oid = i.indexrelid
         WHERE c.oid = pg_catalog.to_regclass('public.ix_student_submissions_id_tenant_gate738e')
    """)).mappings().one_or_none()
    if index is None or not index["indisunique"] or not index["indisvalid"]:
        raise RuntimeError("Gate738E parent identity index is absent or invalid; stop for review")

    constraint_exists = bind.scalar(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_catalog.pg_constraint
             WHERE conrelid = 'public.student_submissions'::regclass
               AND conname = 'uq_submission_identity_tenant'
        )
    """))
    if not constraint_exists:
        op.execute("""
            ALTER TABLE public.student_submissions
            ADD CONSTRAINT uq_submission_identity_tenant
            UNIQUE USING INDEX ix_student_submissions_id_tenant_gate738e
        """)


def downgrade() -> None:
    raise RuntimeError("Gate738E candidate lineage is not safely downgradeable")
