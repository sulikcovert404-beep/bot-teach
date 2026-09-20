from datetime import datetime, timezone

from app.api.routes.teacher import _assignment_payload
from app.db.models import Assignment
from app.domain.assignment import Assignment as DomainAssignment
from app.domain.assignment import AssignmentStatus, assignment_status_at, can_student_submit


def test_persisted_assignment_columns_are_timezone_aware():
    assert Assignment.__table__.c.publish_at.type.timezone is True
    assert Assignment.__table__.c.close_at.type.timezone is True


def test_teacher_payload_serializes_utc_iso8601():
    value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assignment = Assignment(id=1, title="t", instructions="i", status="PUBLISHED", close_at=value)
    payload = _assignment_payload(assignment)
    assert payload["close_at"] == value.isoformat()


def test_domain_boundaries_accept_utc_aware_values_without_type_error():
    published = datetime(2026, 1, 2, tzinfo=timezone.utc)
    closed = datetime(2026, 1, 3, tzinfo=timezone.utc)
    assignment = DomainAssignment(assignment_id="a", tenant_id="t", teacher_id="1", classroom_id="c", status=AssignmentStatus.PUBLISHED, publish_at=published, due_at=published, close_at=closed)
    assert assignment_status_at(assignment, now=published) is AssignmentStatus.PAST_DUE
    assert can_student_submit(student_tenant_id="t", assignment=assignment, enrolled=True, entitled=True, now=published)
    assert not can_student_submit(student_tenant_id="t", assignment=assignment, enrolled=True, entitled=True, now=closed)

