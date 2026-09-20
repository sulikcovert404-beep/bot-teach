"""add school and class persistence foundation"""
import sqlalchemy as sa
from alembic import op

revision = "20260909_0013"
down_revision = "20260909_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teacher_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("teacher_id", "tenant_id", name="uq_teacher_profiles_teacher_tenant"),
    )
    op.create_index("ix_teacher_profiles_teacher_id", "teacher_profiles", ["teacher_id"])
    op.create_index("ix_teacher_profiles_tenant_id", "teacher_profiles", ["tenant_id"])
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("student_id", name="uq_student_profiles_student_id"),
    )
    op.create_index("ix_student_profiles_student_id", "student_profiles", ["student_id"])
    op.create_table(
        "classrooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("classroom_key", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), sa.ForeignKey("teacher_profiles.id"), nullable=False),
        sa.UniqueConstraint("tenant_id", "classroom_key", name="uq_classrooms_tenant_key"),
    )
    op.create_index("ix_classrooms_classroom_key", "classrooms", ["classroom_key"])
    op.create_index("ix_classrooms_tenant_id", "classrooms", ["tenant_id"])
    op.create_index("ix_classrooms_teacher_profile_id", "classrooms", ["teacher_profile_id"])
    op.create_table(
        "class_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("classroom_id", sa.Integer(), sa.ForeignKey("classrooms.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id"), nullable=False),
        sa.UniqueConstraint("classroom_id", "student_id", name="uq_class_memberships_class_student"),
    )
    op.create_index("ix_class_memberships_classroom_id", "class_memberships", ["classroom_id"])
    op.create_index("ix_class_memberships_student_id", "class_memberships", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_class_memberships_student_id", table_name="class_memberships")
    op.drop_index("ix_class_memberships_classroom_id", table_name="class_memberships")
    op.drop_table("class_memberships")
    op.drop_index("ix_classrooms_teacher_profile_id", table_name="classrooms")
    op.drop_index("ix_classrooms_tenant_id", table_name="classrooms")
    op.drop_index("ix_classrooms_classroom_key", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_index("ix_student_profiles_student_id", table_name="student_profiles")
    op.drop_table("student_profiles")
    op.drop_index("ix_teacher_profiles_tenant_id", table_name="teacher_profiles")
    op.drop_index("ix_teacher_profiles_teacher_id", table_name="teacher_profiles")
    op.drop_table("teacher_profiles")
