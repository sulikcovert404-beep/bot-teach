import pytest

from app.security.admin_scope import AdminScope, authorize_scope, require_scope


def test_school_admin_is_limited_to_own_tenant():
    p=AdminScope("a","SCHOOL_ADMIN","school-a")
    assert authorize_scope(principal=p,requested_tenant="school-a")
    assert not authorize_scope(principal=p,requested_tenant="school-b")
    assert not authorize_scope(principal=p,requested_tenant=None)

def test_teacher_is_limited_to_own_tenant():
    p=AdminScope("t","TEACHER","school-a")
    assert authorize_scope(principal=p,requested_tenant="school-a")
    with pytest.raises(PermissionError): require_scope(principal=p,requested_tenant="school-b")

def test_super_admin_explicit_scope_only():
    p=AdminScope("s","SUPER_ADMIN",None)
    assert authorize_scope(principal=p,requested_tenant="school-b")
    assert authorize_scope(principal=p,requested_tenant=None)

def test_student_and_missing_context_fail_closed():
    for p in (AdminScope("u","STUDENT",None),AdminScope("a","SCHOOL_ADMIN",None)):
        assert not authorize_scope(principal=p,requested_tenant="school-a")
