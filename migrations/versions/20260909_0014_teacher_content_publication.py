"""add teacher content publication ownership and classroom binding"""
import sqlalchemy as sa
from alembic import op

revision = "20260909_0014"
down_revision = "20260909_0013"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("content_versions", sa.Column("owner_teacher_id", sa.Integer(), nullable=True))
    op.create_index("ix_content_versions_owner_teacher_id", "content_versions", ["owner_teacher_id"])
    op.create_foreign_key("fk_content_versions_owner_teacher_id_users", "content_versions", "users", ["owner_teacher_id"], ["id"])
    op.create_table(
        "teacher_content_publications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_version_id", sa.Integer(), sa.ForeignKey("content_versions.id"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("classroom_id", sa.Integer(), sa.ForeignKey("classrooms.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PUBLISHED"),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("content_version_id", "classroom_id", name="uq_teacher_content_publication_version_classroom"),
    )
    for col in ("content_version_id", "teacher_id", "classroom_id"):
        op.create_index("ix_teacher_content_publications_" + col, "teacher_content_publications", [col])

def downgrade() -> None:
    op.drop_table("teacher_content_publications")
    op.drop_constraint("fk_content_versions_owner_teacher_id_users", "content_versions", type_="foreignkey")
    op.drop_index("ix_content_versions_owner_teacher_id", table_name="content_versions")
    op.drop_column("content_versions", "owner_teacher_id")
