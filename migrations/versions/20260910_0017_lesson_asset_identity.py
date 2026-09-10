"""Add provider-neutral lesson asset identity fields.

Disposable qualification only.  Legacy generated assets remain valid with NULL
identity fields; Lesson Pack writers must provide all three fields.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_0017"
down_revision = "20260910_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generated_assets", sa.Column("school_stage", sa.String(length=32), nullable=True))
    op.add_column("generated_assets", sa.Column("language", sa.String(length=32), nullable=True))
    op.add_column("generated_assets", sa.Column("profile_version", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_generated_asset_lesson_identity",
        "generated_assets",
        ["job_id", "asset_type", "school_stage", "language", "profile_version"],
        unique=True,
        postgresql_where=sa.text(
            "school_stage IS NOT NULL AND language IS NOT NULL AND profile_version IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_generated_asset_lesson_identity", table_name="generated_assets")
    op.drop_column("generated_assets", "profile_version")
    op.drop_column("generated_assets", "language")
    op.drop_column("generated_assets", "school_stage")
