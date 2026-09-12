import pytest

from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken, RuntimeAdmissionBundle
from app.services.runtime_execution_boundary import (
    BoundaryOutcome,
    ExecutionBoundaryContract,
    ExecutionScope,
    build_execution_boundary,
    evaluate_boundary,
)


def ref(name: str, status=ReferenceStatus.VALID, digest=None):
    return ReferenceToken(name, digest or ("sha256:" + name.encode().hex().ljust(64, "0")[:64]), status)


def bundle():
    return RuntimeAdmissionBundle(
        "bundle-1", "PUBLISH", ref("release"), ref("stage"), ref("entry"), ref("env"),
        (ref("evidence"),), (ref("validation"),), ref("trace"),
    )


def boundary(b, **changes):
    values = dict(
        boundary_id="boundary-1", admission_bundle_reference=ref("bundle", digest=b.bundle_digest),
        execution_scope=ExecutionScope.CONTROLLED_EXECUTION,
        allowed_operations=frozenset({"SYNC_VECTOR"}), denied_operations=frozenset({"DROP_ALL"}),
        actor_reference="system:admin", trace_reference=ref("boundary-trace"),
    )
    values.update(changes)
    return ExecutionBoundaryContract(**values)


def test_valid_boundary_accepts_explicit_operation():
    b = bundle()
    assert evaluate_boundary(boundary(b), b, "SYNC_VECTOR") is BoundaryOutcome.ACCEPTED


def test_scope_and_denied_operation_are_rejected():
    b = bundle(); item = boundary(b)
    assert evaluate_boundary(item, b, "DROP_ALL") is BoundaryOutcome.REJECTED
    assert evaluate_boundary(item, b, "UNDECLARED") is BoundaryOutcome.REJECTED


def test_blocked_admission_and_missing_bundle_are_blocked():
    b = bundle(); blocked = RuntimeAdmissionBundle(
        "blocked", "PUBLISH", ref("release"), ref("stage", ReferenceStatus.BLOCKED), ref("entry"),
        ref("env"), (ref("evidence"),), (ref("validation"),), ref("trace"),
    )
    assert evaluate_boundary(boundary(b), blocked, "SYNC_VECTOR") is BoundaryOutcome.BLOCKED
    with pytest.raises(ValueError):
        boundary(b, admission_bundle_reference=None)


def test_digest_and_actor_binding_are_enforced():
    b = bundle(); item = boundary(b)
    object.__setattr__(item, "boundary_digest", "sha256:" + "0" * 64)
    assert evaluate_boundary(item, b, "SYNC_VECTOR") is BoundaryOutcome.BLOCKED
    assert evaluate_boundary(boundary(b), b, "SYNC_VECTOR", actor_reference="system:other") is BoundaryOutcome.BLOCKED


def test_overlap_is_rejected():
    b = bundle()
    with pytest.raises(ValueError):
        boundary(b, allowed_operations=frozenset({"X"}), denied_operations=frozenset({"X"}))


def test_deterministic_serialization_and_unicode_safety():
    b = bundle(); first = boundary(b, boundary_id="مرحله پیش‌نویس")
    second = boundary(b, boundary_id="مرحله پیش‌نویس")
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.boundary_digest == second.boundary_digest
    assert "پیش‌نویس".encode() in first.canonical_bytes()
    with pytest.raises(AttributeError):
        first.actor_reference = "other"


def test_invalid_reference_status_blocks_boundary_evaluation():
    b = bundle(); item = boundary(b, trace_reference=ref("trace", ReferenceStatus.INVALID))
    assert evaluate_boundary(item, b, "SYNC_VECTOR") is BoundaryOutcome.BLOCKED
