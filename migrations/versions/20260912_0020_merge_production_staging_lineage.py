"""Merge production lineage (20260909_0009) and staging lineage (20260910_0019).

Revision ID: 20260912_0020
Revises: 20260909_0009, 20260910_0019
Create Date: 2026-09-12 10:30:00.000000

Lineage Convergence Contract:
1. When migrating from Staging (0019):
   - beta_feedbacks & beta_quality_audits already exist (from 20260907_0008).
   - users.telegram_user_id is integer; must be altered to BIGINT (satisfies 2e0b56730806).
2. When migrating from Production (0009):
   - beta_feedbacks & beta_quality_audits already exist (from 20260909_0009).
   - users.telegram_user_id is already BIGINT (from 2e0b56730806).
   - All intermediate staging tables (0010 through 0019) are applied in DAG order by Alembic.
   - On reaching 0020, users.telegram_user_id is already BIGINT (idempotent no-op).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260912_0020"
down_revision: Union[str, Sequence[str], None] = ("20260909_0009", "20260910_0019")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure users.telegram_user_id is BIGINT regardless of entry branch.
    # On production lineage (0009), 2e0b56730806 already ran.
    # On staging lineage (0019), it is currently INTEGER and is upgraded to BIGINT here.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"]: c for c in insp.get_columns("users")}
    tg_col = columns.get("telegram_user_id")
    
    if tg_col is not None:
        # Check if type is already BIGINT
        col_type = str(tg_col["type"]).upper()
        if "BIGINT" not in col_type:
            op.alter_column(
                "users",
                "telegram_user_id",
                existing_type=sa.INTEGER(),
                type_=sa.BIGINT(),
                existing_nullable=True,
            )


def downgrade() -> None:
    # Safe downgrade: keep BIGINT as it accommodates all integer values without truncation.
    pass
