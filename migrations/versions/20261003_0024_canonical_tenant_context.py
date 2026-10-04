"""Install the canonical membership table and database-owned tenant resolver."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0024"
down_revision = "20260921_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_tenant_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "tenant_id", sa.String(64), sa.ForeignKey("school_tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_membership_user_tenant"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','REVOKED','SUSPENDED')",
            name="ck_user_tenant_membership_status",
        ),
    )
    op.create_index("ix_user_tenant_memberships_user_id", "user_tenant_memberships", ["user_id"])
    op.create_index("ix_user_tenant_memberships_tenant_id", "user_tenant_memberships", ["tenant_id"])
    op.create_index("ix_user_tenant_memberships_status", "user_tenant_memberships", ["status"])

    # The function owner is the migration identity. Fully qualify every object
    # and constrain resolution to pg_catalog so caller-controlled schemas cannot
    # shadow dependencies. A NULL result is the fail-closed 0-or-many contract.
    op.execute("""
        CREATE FUNCTION public.resolve_tenant(p_user_id integer)
        RETURNS text
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        DECLARE
            matched_count bigint;
            resolved_tenant text;
        BEGIN
            SELECT count(*), min(m.tenant_id)
              INTO matched_count, resolved_tenant
              FROM public.user_tenant_memberships AS m
             WHERE m.user_id = p_user_id
               AND m.status = 'ACTIVE'
               AND m.revoked_at IS NULL;
            IF matched_count <> 1 THEN
                RETURN NULL;
            END IF;
            RETURN resolved_tenant;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.resolve_tenant(integer) FROM PUBLIC")
    # Roles are provisioned outside schema migrations. If the canonical runtime
    # role already exists, grant only this function; never grant table access.
    op.execute("""
        DO $grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'app_runtime') THEN
                EXECUTE 'GRANT EXECUTE ON FUNCTION public.resolve_tenant(integer) TO app_runtime';
            END IF;
        END
        $grant$
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM public.user_tenant_memberships)")):
        raise RuntimeError("Tenant membership data exists; destructive downgrade is not authorized")
    op.execute("DROP FUNCTION public.resolve_tenant(integer)")
    op.drop_index("ix_user_tenant_memberships_status", table_name="user_tenant_memberships")
    op.drop_index("ix_user_tenant_memberships_tenant_id", table_name="user_tenant_memberships")
    op.drop_index("ix_user_tenant_memberships_user_id", table_name="user_tenant_memberships")
    op.drop_table("user_tenant_memberships")
