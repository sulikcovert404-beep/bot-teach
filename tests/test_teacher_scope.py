import pytest
from app.security.teacher_scope import TeacherClassScope, can_access_class, require_class

def test_teacher_can_access_assigned_class_only():
    s=TeacherClassScope("t1","school-a",frozenset({1,2}))
    assert can_access_class(scope=s,classroom_id=1,tenant_id="school-a")
    assert not can_access_class(scope=s,classroom_id=3,tenant_id="school-a")
    assert not can_access_class(scope=s,classroom_id=1,tenant_id="school-b")

def test_missing_assignment_denies():
    s=TeacherClassScope("t1","school-a",frozenset())
    with pytest.raises(PermissionError): require_class(scope=s,classroom_id=1,tenant_id="school-a")
