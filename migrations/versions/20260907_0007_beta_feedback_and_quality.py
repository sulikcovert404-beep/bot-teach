"""Create beta feedback and quality audit tables

Revision ID: 20260907_0007
Revises: 20260907_0006
Create Date: 2026-09-07 13:16:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260907_0008"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if "beta_feedbacks" not in existing_tables:
        op.create_table(
            "beta_feedbacks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("query", sa.String(length=1000), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("feedback_type", sa.String(length=64), nullable=False),
            sa.Column("comment", sa.String(length=2000), nullable=True),
            sa.Column("source_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_beta_feedbacks_user_id", "beta_feedbacks", ["user_id"])
        op.create_index("ix_beta_feedbacks_feedback_type", "beta_feedbacks", ["feedback_type"])

    if "beta_quality_audits" not in existing_tables:
        op.create_table(
            "beta_quality_audits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("query", sa.String(length=1000), nullable=False),
            sa.Column("model", sa.String(length=128), nullable=False),
            sa.Column("has_citations", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("citations_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("latency_ms", sa.Integer(), nullable=False),
            sa.Column("tokens_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("content_gap_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_beta_quality_audits_user_id", "beta_quality_audits", ["user_id"])

def downgrade() -> None:
    op.drop_table("beta_quality_audits")
    op.drop_table("beta_feedbacks")
