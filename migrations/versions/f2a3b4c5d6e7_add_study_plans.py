"""add persisted study plans

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("daily_minutes", sa.Integer(), nullable=False),
        sa.Column("max_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])
    op.create_table(
        "study_plan_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_plan_tasks_plan_id", "study_plan_tasks", ["plan_id"])
    op.create_index("ix_study_plan_tasks_lesson_id", "study_plan_tasks", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_study_plan_tasks_lesson_id", table_name="study_plan_tasks")
    op.drop_index("ix_study_plan_tasks_plan_id", table_name="study_plan_tasks")
    op.drop_table("study_plan_tasks")
    op.drop_index("ix_study_plans_user_id", table_name="study_plans")
    op.drop_table("study_plans")
