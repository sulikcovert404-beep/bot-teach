"""add flashcard review state

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("flashcards", sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("flashcards", sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("flashcards", sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"))
    op.add_column("flashcards", sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("flashcards", "next_review_at")
    op.drop_column("flashcards", "ease_factor")
    op.drop_column("flashcards", "interval_days")
    op.drop_column("flashcards", "review_count")
