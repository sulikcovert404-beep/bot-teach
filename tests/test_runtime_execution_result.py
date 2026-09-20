import pytest

from app.services.runtime_admission_bundle import (
    ReferenceStatus,
    ReferenceToken,
    RuntimeAdmissionBundle,
)
from app.services.runtime_execution_boundary import ExecutionBoundaryContract, ExecutionScope
from app.services.runtime_execution_result import (
    ExecutionResult,
    ExecutionResultStatus,
    validate_execution_result,
)


def ref(name, status=ReferenceStatus.VALID, digest=None):
    return ReferenceToken(name, digest or ("sha256:" + name.encode().hex().ljust(64, "0")[:64]), status)


def upstream():
    bundle = RuntimeAdmissionBundle("bundle", "PUBLISH", ref("release"), ref("stage"), ref("entry"), ref("env"), (ref("ev"),), (ref("val"),), ref("trace"))
    boundary = ExecutionBoundaryContract("boundary", ref("bundle", digest=bundle.bundle_digest), ExecutionScope.CONTROLLED_EXECUTION, frozenset({"SYNC"}), frozenset(), "system", ref("btrace"))
    return bundle, boundary


def result(status=ExecutionResultStatus.SUCCEEDED, **kwargs):
    bundle, boundary = upstream()
    values = {"execution_id": "exec", "boundary_reference": ref("boundary", digest=boundary.boundary_digest), "admission_bundle_reference": ref("bundle", digest=bundle.bundle_digest), "status": status, "output_reference": ref("output") if status in (ExecutionResultStatus.SUCCEEDED, ExecutionResultStatus.PARTIAL) else None, "evidence_references": (ref("evidence"),) if status is ExecutionResultStatus.PARTIAL else (), "trace_reference": ref("trace"), "failure_reference": ref("failure") if status is ExecutionResultStatus.FAILED else None, "recovery_reference": ref("recovery") if status is ExecutionResultStatus.FAILED else None}
    values.update(kwargs)
    return ExecutionResult(**values), bundle, boundary


def test_success_result_requires_valid_upstream():
    item, bundle, boundary = result()
    assert validate_execution_result(item, boundary, bundle)


def test_missing_boundary_reference_rejected():
    with pytest.raises(ValueError):
        result(boundary_reference=None)


def test_statuses_and_failure_recovery_linkage():
    failed, bundle, boundary = result(ExecutionResultStatus.FAILED)
    assert failed.failure_reference and failed.recovery_reference
    assert validate_execution_result(failed, boundary, bundle)
    blocked, _, _ = result(ExecutionResultStatus.BLOCKED)
    assert blocked.status is ExecutionResultStatus.BLOCKED
    unknown, _, _ = result(ExecutionResultStatus.UNKNOWN)
    assert validate_execution_result(unknown) 


def test_partial_requires_explicit_evidence():
    with pytest.raises(ValueError):
        result(ExecutionResultStatus.PARTIAL, evidence_references=())


def test_unknown_with_output_does_not_validate_as_success():
    item, _, _ = result(ExecutionResultStatus.UNKNOWN, output_reference=ref("output"))
    assert not validate_execution_result(item)


def test_digest_mismatch_and_binding_are_invalid():
    item, bundle, boundary = result()
    object.__setattr__(item, "result_digest", "sha256:" + "0" * 64)
    assert not validate_execution_result(item, boundary, bundle)
    item, _, _ = result()
    assert not validate_execution_result(item, None, RuntimeAdmissionBundle("other", "PUBLISH", ref("r"), ref("s"), ref("e"), ref("env"), (ref("ev"),), (ref("v"),), ref("t")))


def test_deterministic_serialization_and_persian_safety():
    a, _, _ = result(execution_id="اجرا‌شده")
    b, _, _ = result(execution_id="اجرا‌شده")
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.result_digest == b.result_digest
    assert "اجرا‌شده".encode() in a.canonical_bytes()


def test_secret_like_reference_rejected():
    with pytest.raises(ValueError):
        result(trace_reference=ref("token=secret"))
