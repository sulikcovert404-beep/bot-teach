"""complete generation attempt audit fields"""
from alembic import op
import sqlalchemy as sa
revision = "20260909_0012"
down_revision = "20260909_0011"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column("generation_attempts", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("generation_attempts", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("generation_attempts", sa.Column("cost", sa.Float(), nullable=False, server_default="0"))
def downgrade() -> None:
    op.drop_column("generation_attempts", "cost"); op.drop_column("generation_attempts", "completed_at"); op.drop_column("generation_attempts", "started_at")
