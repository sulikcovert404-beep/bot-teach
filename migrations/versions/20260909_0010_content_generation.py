"""add content generation lifecycle tables"""
import sqlalchemy as sa
from alembic import op

revision = "20260909_0010"
down_revision = "20260907_0008"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("content_generation_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_version_id", sa.Integer, sa.ForeignKey("content_versions.id"), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("requested_by", sa.Integer, sa.ForeignKey("users.id")), sa.Column("tenant_id", sa.String(255)),
        sa.Column("provider", sa.String(64)), sa.Column("model", sa.String(128)), sa.Column("generation_parameters_hash", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64)), sa.Column("output_reference", sa.String(255)), sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("content_version_id", "asset_type", "generation_parameters_hash"))
    op.create_index("ix_content_generation_jobs_status", "content_generation_jobs", ["status"])
    op.create_table("generation_attempts", sa.Column("id", sa.Integer, primary_key=True), sa.Column("job_id", sa.Integer, sa.ForeignKey("content_generation_jobs.id"), nullable=False), sa.Column("provider", sa.String(64)), sa.Column("model", sa.String(128)), sa.Column("outcome", sa.String(32), nullable=False), sa.Column("error_code", sa.String(64)), sa.Column("token_usage", sa.Integer, nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_generation_attempts_job_id", "generation_attempts", ["job_id"])
    op.create_table("generated_assets", sa.Column("id", sa.Integer, primary_key=True), sa.Column("job_id", sa.Integer, sa.ForeignKey("content_generation_jobs.id"), nullable=False, unique=True), sa.Column("asset_type", sa.String(64), nullable=False), sa.Column("content_json", sa.Text, nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("review_state", sa.String(32), nullable=False, server_default="DRAFT"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

def downgrade() -> None:
    op.drop_table("generated_assets"); op.drop_table("generation_attempts"); op.drop_table("content_generation_jobs")
