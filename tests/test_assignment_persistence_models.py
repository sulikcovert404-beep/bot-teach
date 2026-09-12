from app.db.models import Assignment, AssignmentSnapshot, AssignmentTarget, StudentSubmission, SubmissionReview


def test_assignment_persistence_tables_and_constraints():
    assert {Assignment.__tablename__, AssignmentSnapshot.__tablename__, AssignmentTarget.__tablename__, StudentSubmission.__tablename__, SubmissionReview.__tablename__} == {
        "assignments", "assignment_snapshots", "assignment_targets", "student_submissions", "submission_reviews"
    }
    assert any(c.name == "uq_student_submissions_current" for c in StudentSubmission.__table__.constraints)
    assert any(c.name == "ck_assignments_status" for c in Assignment.__table__.constraints)
    assert any(c.name == "uq_assignment_snapshots_version" for c in AssignmentSnapshot.__table__.constraints)


def test_tenant_columns_present_on_all_assignment_tables():
    for model in (Assignment, AssignmentSnapshot, AssignmentTarget, StudentSubmission, SubmissionReview):
        assert "tenant_id" in model.__table__.c
