"""Add provisioning idempotency persistence."""
import sqlalchemy as sa
from alembic import op

revision = "20260921_0022"
down_revision = "20260912_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provisioning_idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CLAIMED"),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("response_json", sa.String(length=8000), nullable=False, server_default="{}"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('CLAIMED', 'SUCCEEDED')", name="ck_provisioning_idempotency_status"),
        sa.UniqueConstraint("operation", "idempotency_key", name="uq_provisioning_idempotency_operation_key"),
    )
    op.create_index("ix_provisioning_idempotency_keys_operation", "provisioning_idempotency_keys", ["operation"])
    op.create_index("ix_provisioning_idempotency_keys_idempotency_key", "provisioning_idempotency_keys", ["idempotency_key"])
    op.create_index("ix_provisioning_idempotency_keys_status", "provisioning_idempotency_keys", ["status"])
    op.create_index("ix_provisioning_idempotency_keys_actor_user_id", "provisioning_idempotency_keys", ["actor_user_id"])
    op.create_index("ix_provisioning_idempotency_keys_correlation_id", "provisioning_idempotency_keys", ["correlation_id"])
    op.create_index("ix_provisioning_idempotency_keys_user_id", "provisioning_idempotency_keys", ["user_id"])


def downgrade() -> None:
    op.drop_table("provisioning_idempotency_keys")
