"""Mark completion of the guarded, staged submission revision contract."""

from alembic import op

revision = "20261004_0033"
down_revision = "20261003_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from migrations.gate738p_contract_guard import assert_contract_preconditions

    assert_contract_preconditions(op.get_bind())


def downgrade() -> None:
    raise RuntimeError("Gate738P contract completion is forward-only")
