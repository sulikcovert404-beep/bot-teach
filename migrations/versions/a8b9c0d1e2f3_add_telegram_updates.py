"""add Telegram webhook idempotency records

Revision ID: a8b9c0d1e2f3
Revises: f2a3b4c5d6e7
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("update_id"),
    )
    op.create_index("ix_telegram_updates_update_id", "telegram_updates", ["update_id"])


def downgrade() -> None:
    op.drop_index("ix_telegram_updates_update_id", table_name="telegram_updates")
    op.drop_table("telegram_updates")
