import pytest

from app.services.runtime_execution_lifecycle import (
    LifecycleOutcome,
    LifecycleState,
    build_execution_lifecycle,
    validate_execution_lifecycle,
)
from app.services.runtime_execution_result import ExecutionResultStatus
from tests.test_runtime_execution_result import ref, result, upstream


def life(state=LifecycleState.RUNNING, prev=LifecycleState.ADMITTED, result_ref=None):
    bundle,boundary=upstream()
    return build_execution_lifecycle(execution_id="exec",current_state=state,previous_state=prev,transition_reference=ref("transition"),boundary_reference=ref("boundary",digest=boundary.boundary_digest),result_reference=result_ref,trace_reference=ref("trace")),bundle,boundary

def test_valid_lifecycle_and_result_binding():
    item,boundary_bundle,boundary=result()
    lc,_,_=life(LifecycleState.SUCCEEDED,LifecycleState.RUNNING,ref("result",digest=item.result_digest))
    assert validate_execution_lifecycle(lc,item,boundary) is LifecycleOutcome.VALID

def test_invalid_transition_and_terminal_protection():
    lc,_,_=life(LifecycleState.CREATED,LifecycleState.SUCCEEDED)
    assert validate_execution_lifecycle(lc) is LifecycleOutcome.INVALID
    terminal,_,_=life(LifecycleState.RUNNING,LifecycleState.SUCCEEDED)
    assert validate_execution_lifecycle(terminal) is LifecycleOutcome.INVALID

def test_failed_result_binding_and_blocked_recovery_path():
    item,_,boundary=result(ExecutionResultStatus.FAILED)
    lc,_,_=life(LifecycleState.FAILED,LifecycleState.RUNNING,ref("result",digest=item.result_digest))
    assert validate_execution_lifecycle(lc,item,boundary) is LifecycleOutcome.VALID
    blocked,_,_=life(LifecycleState.BLOCKED,LifecycleState.RUNNING)
    assert validate_execution_lifecycle(blocked) is LifecycleOutcome.BLOCKED
    recovered,_,_=life(LifecycleState.ADMITTED,LifecycleState.BLOCKED)
    assert validate_execution_lifecycle(recovered) is LifecycleOutcome.VALID

def test_digest_mismatch_and_deterministic_unicode_serialization():
    a,_,_=life(LifecycleState.RUNNING,LifecycleState.ADMITTED)
    b,_,_=life(LifecycleState.RUNNING,LifecycleState.ADMITTED)
    assert a.canonical_bytes()==b.canonical_bytes() and a.lifecycle_digest==b.lifecycle_digest
    assert "اجرا‌شده".encode() not in a.canonical_bytes()
    object.__setattr__(a,"lifecycle_digest","sha256:"+"0"*64)
    assert validate_execution_lifecycle(a) is LifecycleOutcome.INVALID

def test_result_state_mismatch_invalid():
    item,_,boundary=result(ExecutionResultStatus.UNKNOWN)
    lc,_,_=life(LifecycleState.SUCCEEDED,LifecycleState.RUNNING,ref("result",digest=item.result_digest))
    assert validate_execution_lifecycle(lc,item,boundary) is LifecycleOutcome.INVALID

def test_required_references_and_secret_rejection():
    bundle,boundary=upstream()
    with pytest.raises(ValueError): build_execution_lifecycle(execution_id="exec",current_state=LifecycleState.CREATED,previous_state=None,transition_reference=None,boundary_reference=ref("boundary",digest=boundary.boundary_digest),result_reference=None,trace_reference=ref("trace"))
    with pytest.raises(ValueError): build_execution_lifecycle(execution_id="exec",current_state=LifecycleState.CREATED,previous_state=None,transition_reference=ref("transition"),boundary_reference=ref("boundary",digest=boundary.boundary_digest),result_reference=None,trace_reference=ref("token=secret"))


