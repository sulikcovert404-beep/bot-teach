"""Add tenant-aware exam assignment and attempt persistence (disposable qualification)."""
import sqlalchemy as sa
from alembic import op

revision = "20260912_0021"
down_revision = "20260912_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    exam_cols = {c["name"] for c in insp.get_columns("exams")}
    if "tenant_id" not in exam_cols:
        op.add_column("exams", sa.Column("tenant_id", sa.String(64), nullable=True))
        op.create_index("ix_exams_tenant_id", "exams", ["tenant_id"])
        # Deterministic ownership derivation; never guess a tenant.
        op.execute("""UPDATE exams e SET tenant_id = tp.tenant_id
                       FROM teacher_profiles tp
                       WHERE tp.teacher_id = e.user_id AND e.tenant_id IS NULL""")
        unresolved = bind.execute(sa.text("SELECT count(*) FROM exams WHERE tenant_id IS NULL")).scalar_one()
        if unresolved:
            raise RuntimeError(f"exam tenant backfill unresolved rows: {unresolved}")
        op.alter_column("exams", "tenant_id", existing_type=sa.String(64), nullable=False)
    assignment_cols = {c["name"] for c in insp.get_columns("assignments")}
    if "exam_id" not in assignment_cols:
        op.add_column("assignments", sa.Column("exam_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_assignments_exam_id", "assignments", "exams", ["exam_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_assignments_exam_id", "assignments", ["exam_id"])
    tables = set(insp.get_table_names())
    if "exam_attempts" not in tables:
        op.create_table(
            "exam_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("attempt_no", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="STARTED"),
            sa.Column("question_snapshot", sa.Text(), nullable=False),
            sa.Column("answer_payload", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("last_saved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("assignment_id", "student_id", "attempt_no", name="uq_exam_attempt_identity"),
            sa.CheckConstraint("status IN ('STARTED', 'IN_PROGRESS', 'SUBMITTED', 'GRADED')", name="ck_exam_attempt_status"),
        )
        op.create_index("ix_exam_attempts_tenant_id", "exam_attempts", ["tenant_id"])
        op.create_index("ix_exam_attempts_assignment_id", "exam_attempts", ["assignment_id"])
        op.create_index("ix_exam_attempts_student_id", "exam_attempts", ["student_id"])
        op.create_index("ix_exam_attempts_status", "exam_attempts", ["status"])
    if "exam_results" not in tables:
        op.create_table(
            "exam_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("max_score", sa.Float(), nullable=False),
            sa.Column("grading_status", sa.String(32), nullable=False, server_default="GRADED"),
            sa.Column("grading_source", sa.String(64), nullable=False, server_default="server"),
            sa.Column("graded_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_exam_results_tenant_id", "exam_results", ["tenant_id"])
        op.create_index("ix_exam_results_attempt_id", "exam_results", ["attempt_id"])
        op.create_index("ix_exam_results_grading_status", "exam_results", ["grading_status"])
    # Composite tenant-aware references prevent cross-tenant ID splicing.
    for table, name in (("exams", "uq_exams_id_tenant"), ("assignments", "uq_assignments_id_tenant"), ("exam_attempts", "uq_exam_attempts_id_tenant")):
        existing = {c["name"] for c in sa.inspect(bind).get_unique_constraints(table)}
        if name not in existing:
            op.create_unique_constraint(name, table, ["id", "tenant_id"])
    if "fk_assignments_exam_tenant" not in {c["name"] for c in sa.inspect(bind).get_foreign_keys("assignments")}:
        op.create_foreign_key("fk_assignments_exam_tenant", "assignments", "exams", ["exam_id", "tenant_id"], ["id", "tenant_id"])
    if "fk_attempts_assignment_tenant" not in {c["name"] for c in sa.inspect(bind).get_foreign_keys("exam_attempts")}:
        op.create_foreign_key("fk_attempts_assignment_tenant", "exam_attempts", "assignments", ["assignment_id", "tenant_id"], ["id", "tenant_id"])
    if "fk_results_attempt_tenant" not in {c["name"] for c in sa.inspect(bind).get_foreign_keys("exam_results")}:
        op.create_foreign_key("fk_results_attempt_tenant", "exam_results", "exam_attempts", ["attempt_id", "tenant_id"], ["id", "tenant_id"])
    # Fail-closed tenant policies; runtime roles must set app.tenant_id transaction-locally.
    for table in ("exams", "exam_attempts", "exam_results"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(f'''DROP POLICY IF EXISTS tenant_isolation ON "{table}"''')
        op.execute(f'''CREATE POLICY tenant_isolation ON "{table}"
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true))''')


def downgrade() -> None:
    for table in ("exam_results", "exam_attempts", "exams"):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"')
        if table != "exams":
            op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    for table, name in (("exam_results", "fk_results_attempt_tenant"), ("exam_attempts", "fk_attempts_assignment_tenant"), ("assignments", "fk_assignments_exam_tenant"), ("exam_attempts", "uq_exam_attempts_id_tenant"), ("assignments", "uq_assignments_id_tenant"), ("exams", "uq_exams_id_tenant")):
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{name}"')
    op.drop_table("exam_results")
    op.drop_table("exam_attempts")
    op.drop_index("ix_assignments_exam_id", table_name="assignments")
    op.drop_constraint("fk_assignments_exam_id", "assignments", type_="foreignkey")
    op.drop_column("assignments", "exam_id")
    op.drop_index("ix_exams_tenant_id", table_name="exams")
    op.drop_column("exams", "tenant_id")
