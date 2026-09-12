"""Add persisted school-admin tenant memberships for scoped dashboards."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_0019"
down_revision = "20260910_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The ORM has exposed SchoolTenant since the school/class foundation, but
    # no migration previously owned its table. Create that canonical parent
    # before adding the admin membership FK.
    op.create_table(
        "school_tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("school_name", sa.String(length=150), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False, server_default="Tehran - District 6"),
        sa.Column("max_student_quota", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("max_teacher_quota", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("licensing_status", sa.String(length=30), nullable=False, server_default="PILOT_ACTIVE"),
        sa.Column("data_isolation_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_school_tenants_tenant_id", "school_tenants", ["tenant_id"])
    op.create_table(
        "school_admin_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), sa.ForeignKey("school_tenants.tenant_id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_school_admin_membership_user_tenant"),
    )
    op.create_index("ix_school_admin_memberships_user_id", "school_admin_memberships", ["user_id"])
    op.create_index("ix_school_admin_memberships_tenant_id", "school_admin_memberships", ["tenant_id"])
    op.create_index("ix_school_admin_memberships_status", "school_admin_memberships", ["status"])


def downgrade() -> None:
    op.drop_index("ix_school_admin_memberships_status", table_name="school_admin_memberships")
    op.drop_index("ix_school_admin_memberships_tenant_id", table_name="school_admin_memberships")
    op.drop_index("ix_school_admin_memberships_user_id", table_name="school_admin_memberships")
    op.drop_table("school_admin_memberships")
    op.drop_index("ix_school_tenants_tenant_id", table_name="school_tenants")
    op.drop_table("school_tenants")
