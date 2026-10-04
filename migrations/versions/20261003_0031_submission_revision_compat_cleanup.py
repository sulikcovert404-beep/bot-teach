"""Atomically fence legacy writes while preserving a candidate-only guard."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0031"
down_revision = "20261003_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from migrations.gate738p_contract_guard import assert_contract_preconditions

    assert_contract_preconditions(op.get_bind())
    # Each compatibility trigger takes FOR SHARE on the singleton rollout row
    # for the duration of its transaction. This UPDATE is the DB-owned fence:
    # it waits for in-flight writers, blocks new compatibility writes, then
    # atomically switches their trigger behavior to fail-closed. Candidate
    # writes already carry their exact immutable revision and remain valid.
    result = op.get_bind().execute(sa.text("""
        UPDATE public.submission_revision_rollout_state
           SET status='CONTRACTED'
         WHERE singleton=true AND status='COMPATIBILITY'
    """))
    if result.rowcount != 1:
        raise RuntimeError("revision rollout fence was not in COMPATIBILITY state; refusing contract")


def downgrade() -> None:
    raise RuntimeError("Gate738E legacy bridge cleanup requires a new forward-only release")
