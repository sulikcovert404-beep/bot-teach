"""add worker lease fields"""
import sqlalchemy as sa
from alembic import op

revision = "20260909_0011"
down_revision = "20260909_0010"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column("content_generation_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.add_column("content_generation_jobs", sa.Column("worker_id", sa.String(128)))
    op.create_index("ix_content_generation_jobs_lease_expires_at", "content_generation_jobs", ["lease_expires_at"])
def downgrade() -> None:
    op.drop_index("ix_content_generation_jobs_lease_expires_at", table_name="content_generation_jobs")
    op.drop_column("content_generation_jobs", "worker_id")
    op.drop_column("content_generation_jobs", "lease_expires_at")
