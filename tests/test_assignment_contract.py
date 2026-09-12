from datetime import UTC, datetime, timedelta

from app.domain.assignment import (
    Assignment,
    AssignmentStatus,
    assignment_status_at,
    can_student_read,
    can_student_submit,
    can_teacher_manage,
)


def make_assignment(**kwargs):
    values = dict(assignment_id="a1", teacher_id="t1", classroom_id="c1", tenant_id="tenant-a")
    values.update(kwargs)
    return Assignment(**values)


def test_teacher_scope_and_tenant_are_enforced():
    assignment = make_assignment()
    assert can_teacher_manage(teacher_id="t1", assignment=assignment, tenant_id="tenant-a", classroom_ids={"c1"})
    assert not can_teacher_manage(teacher_id="t2", assignment=assignment, tenant_id="tenant-a", classroom_ids={"c1"})
    assert not can_teacher_manage(teacher_id="t1", assignment=assignment, tenant_id="tenant-b", classroom_ids={"c1"})


def test_student_requires_published_membership_and_entitlement():
    assignment = make_assignment(status=AssignmentStatus.PUBLISHED)
    now = datetime.now(UTC)
    assert can_student_read(student_tenant_id="tenant-a", assignment=assignment, enrolled=True, entitled=True, now=now)
    assert not can_student_read(student_tenant_id="tenant-a", assignment=assignment, enrolled=False, entitled=True, now=now)
    assert not can_student_read(student_tenant_id="tenant-a", assignment=assignment, enrolled=True, entitled=False, now=now)
    assert not can_student_read(student_tenant_id="tenant-b", assignment=assignment, enrolled=True, entitled=True, now=now)


def test_due_and_close_are_server_time_derived():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assignment = make_assignment(status=AssignmentStatus.PUBLISHED, due_at=now - timedelta(seconds=1), close_at=now + timedelta(seconds=1))
    assert assignment_status_at(assignment, now=now) is AssignmentStatus.PAST_DUE
    assert can_student_submit(student_tenant_id="tenant-a", assignment=assignment, enrolled=True, entitled=True, now=now)
    assert not can_student_submit(student_tenant_id="tenant-a", assignment=assignment, enrolled=True, entitled=True, now=now + timedelta(seconds=2))


def test_draft_is_not_student_visible():
    assignment = make_assignment()
    assert not can_student_read(student_tenant_id="tenant-a", assignment=assignment, enrolled=True, entitled=True, now=datetime.now(UTC))
