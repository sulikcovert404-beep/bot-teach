"""change telegram user id to bigint"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "2e0b56730806"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column("users", "telegram_user_id", existing_type=sa.INTEGER(), type_=sa.BIGINT(), existing_nullable=True)

def downgrade() -> None:
    op.alter_column("users", "telegram_user_id", existing_type=sa.BIGINT(), type_=sa.INTEGER(), existing_nullable=True)
