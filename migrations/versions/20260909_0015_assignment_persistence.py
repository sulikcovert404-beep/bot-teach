"""add assignment v1 persistence tables"""
import sqlalchemy as sa
from alembic import op

revision = "20260909_0015"
down_revision = "20260909_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("classroom_id", sa.Integer(), sa.ForeignKey("classrooms.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("publish_at", sa.DateTime(timezone=True)), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("close_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_assignments_tenant_idempotency"),
        sa.CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'CLOSED')", name="ck_assignments_status"),
    )
    op.create_table("assignment_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("content_digest", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("assignment_id", "version", name="uq_assignment_snapshots_version"))
    op.create_table("assignment_targets", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("classroom_id", sa.Integer(), sa.ForeignKey("classrooms.id"), nullable=False), sa.Column("tenant_id", sa.String(64), nullable=False), sa.UniqueConstraint("assignment_id", "classroom_id", name="uq_assignment_targets_classroom"))
    op.create_table("student_submissions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id"), nullable=False), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="NOT_SUBMITTED"), sa.Column("content_json", sa.Text()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("assignment_id", "student_id", name="uq_student_submissions_current"), sa.CheckConstraint("status IN ('NOT_SUBMITTED', 'SUBMITTED', 'REVIEWED')", name="ck_student_submissions_status"))
    op.create_table("submission_reviews", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("submission_id", sa.Integer(), sa.ForeignKey("student_submissions.id", ondelete="CASCADE"), nullable=False), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("review_status", sa.String(32), nullable=False, server_default="PENDING"), sa.Column("score", sa.Float()), sa.Column("teacher_feedback", sa.Text()), sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("submission_id", name="uq_submission_reviews_submission"))
    op.create_table("assignment_statuses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("assignment_id", name="uq_assignment_status_assignment"))
    for table, cols in {"assignments":["tenant_id","teacher_id","classroom_id"],"assignment_snapshots":["assignment_id","tenant_id"],"assignment_targets":["assignment_id","classroom_id","tenant_id"],"student_submissions":["assignment_id","student_id","tenant_id"],"submission_reviews":["submission_id","tenant_id"],"assignment_statuses":["assignment_id","tenant_id"]}.items():
        for col in cols: op.create_index("ix_%s_%s" % (table, col), table, [col])


def downgrade() -> None:
    for table in ("submission_reviews", "student_submissions", "assignment_targets", "assignment_snapshots", "assignment_statuses", "assignments"):
        op.drop_table(table)
