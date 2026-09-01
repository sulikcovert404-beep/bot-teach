"""store the plan on payment transactions

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_transactions",
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="FREE"),
    )


def downgrade() -> None:
    op.drop_column("payment_transactions", "plan")
