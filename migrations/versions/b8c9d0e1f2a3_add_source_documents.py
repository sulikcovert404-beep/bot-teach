"""add source documents and chunks

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("uri", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_source_documents_source_id", "source_documents", ["source_id"])
    op.create_table(
        "source_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=8000), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_chunks_document_id", "source_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_source_chunks_document_id", table_name="source_chunks")
    op.drop_table("source_chunks")
    op.drop_index("ix_source_documents_source_id", table_name="source_documents")
    op.drop_table("source_documents")
