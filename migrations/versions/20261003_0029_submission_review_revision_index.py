"""Build the future review-to-revision uniqueness index without blocking writes."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0029"
down_revision = "20261003_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_submission_reviews_revision_gate738e "
            "ON public.submission_reviews (submission_revision_id)"
        )
    index = bind.execute(sa.text("""
        SELECT i.indisunique, i.indisvalid
          FROM pg_catalog.pg_index AS i
         WHERE i.indexrelid = pg_catalog.to_regclass(
             'public.ix_submission_reviews_revision_gate738e'
         )
    """)).mappings().one_or_none()
    if index is None or not index["indisunique"] or not index["indisvalid"]:
        raise RuntimeError("Gate738E review identity index is absent or invalid; stop for review")


def downgrade() -> None:
    raise RuntimeError("Gate738E candidate lineage is not safely downgradeable")
