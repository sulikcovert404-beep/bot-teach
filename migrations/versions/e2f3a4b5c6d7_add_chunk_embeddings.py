"""add vector embeddings and retrieval metadata to source chunks

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=64), nullable=True),
        sa.Column("subject", sa.String(length=128), nullable=True),
        sa.Column("chapter", sa.String(length=255), nullable=True),
        sa.Column("lesson", sa.String(length=255), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    ]
    for column in columns:
        op.add_column("source_chunks", column)
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_source_chunks_book_id_books",
            "source_chunks",
            "books",
            ["book_id"],
            ["id"],
        )
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE source_chunks ADD COLUMN embedding vector(768)")
    else:
        op.add_column("source_chunks", sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE source_chunks DROP COLUMN IF EXISTS embedding")
    else:
        op.drop_column("source_chunks", "embedding")
    if bind.dialect.name == "postgresql":
        op.drop_constraint("fk_source_chunks_book_id_books", "source_chunks", type_="foreignkey")
    for name in (
        "embedding_model",
        "content_hash",
        "page_end",
        "page_start",
        "lesson",
        "chapter",
        "subject",
        "grade",
        "book_id",
        "source_type",
    ):
        op.drop_column("source_chunks", name)
