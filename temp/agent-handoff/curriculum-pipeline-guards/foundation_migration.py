"""add additive curriculum pipeline foundation tables"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("content_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("source_documents.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("processing_state", sa.String(32), nullable=False, server_default="UPLOADED"),
        sa.Column("review_state", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("vector_sync_state", sa.String(32), nullable=False, server_default="VECTOR_PENDING"),
        sa.Column("source_hash", sa.String(64)), sa.Column("extracted_hash", sa.String(64)),
        sa.Column("pipeline_digest", sa.String(64)),
        sa.Column("parser_version", sa.String(128)), sa.Column("ocr_config_version", sa.String(128)),
        sa.Column("normalizer_version", sa.String(128)), sa.Column("chunker_version", sa.String(128)),
        sa.Column("provenance_json", sa.String(8000), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_document_id", "version_number"))
    for col in ("source_document_id", "processing_state", "review_state", "vector_sync_state", "source_hash", "pipeline_digest"):
        op.create_index("ix_content_versions_" + col, "content_versions", [col])
    op.create_table("publication_pointers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("source_documents.id"), nullable=False),
        sa.Column("content_version_id", sa.Integer(), sa.ForeignKey("content_versions.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_document_id"))
    op.create_index("ix_publication_pointers_source_document_id", "publication_pointers", ["source_document_id"])
    op.create_index("ix_publication_pointers_content_version_id", "publication_pointers", ["content_version_id"])
    op.create_table("transactional_outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("event_type", sa.String(64), nullable=False), sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False), sa.Column("payload_json", sa.String(12000), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for col in ("event_id", "event_type", "aggregate_id", "status"):
        op.create_index("ix_transactional_outbox_events_" + col, "transactional_outbox_events", [col])
    op.create_table("ingestion_idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("source_documents.id")), sa.Column("request_hash", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACCEPTED"), sa.Column("response_json", sa.String(8000), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_ingestion_idempotency_keys_idempotency_key", "ingestion_idempotency_keys", ["idempotency_key"])
    op.create_index("ix_ingestion_idempotency_keys_source_document_id", "ingestion_idempotency_keys", ["source_document_id"])


def downgrade() -> None:
    op.drop_table("ingestion_idempotency_keys")
    op.drop_table("transactional_outbox_events")
    op.drop_table("publication_pointers")
    op.drop_table("content_versions")
