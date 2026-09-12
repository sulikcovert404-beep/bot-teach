import pytest
from app.services.runtime_execution_lifecycle import LifecycleState
from app.services.runtime_execution_result import ExecutionResultStatus
from app.services.runtime_execution_reconciliation import ReconciliationOutcome,build_reconciliation,validate_reconciliation
from tests.test_runtime_execution_result import ref,upstream,result

def req(expected=LifecycleState.SUCCEEDED,observed=LifecycleState.SUCCEEDED,result_ref=None,evidence=(None,)):
 b,bd=upstream(); ev=tuple(x for x in evidence if x); return build_reconciliation(reconciliation_id="r1",execution_reference=ref("exec"),expected_state=expected,observed_state=observed,result_reference=result_ref,evidence_references=ev,trace_reference=ref("trace"))
def test_consistent_and_conflict():
 r=req(); assert validate_reconciliation(r) is ReconciliationOutcome.CONSISTENT
 assert validate_reconciliation(req(observed=LifecycleState.FAILED)) is ReconciliationOutcome.REQUIRES_RECONCILIATION
def test_unknown_and_digest_blocked():
 assert validate_reconciliation(req(observed=LifecycleState.UNKNOWN)) is ReconciliationOutcome.UNKNOWN
 r=req(); object.__setattr__(r,"digest","sha256:"+"0"*64); assert validate_reconciliation(r) is ReconciliationOutcome.BLOCKED
def test_result_mismatch_and_evidence_trace_binding():
 item,_,_=result(ExecutionResultStatus.SUCCEEDED); r=req(result_ref=ref("wrong",digest=item.result_digest))
 assert validate_reconciliation(r,result=item) is ReconciliationOutcome.BLOCKED
 r=req(result_ref=ref("exec",digest=item.result_digest)); assert validate_reconciliation(r,result=item) is ReconciliationOutcome.CONSISTENT
def test_serialization_and_unicode():
 a=req(); b=req(); assert a.canonical_bytes()==b.canonical_bytes() and a.digest==b.digest
 assert "اجرا‌شده" not in a.canonical_bytes().decode()
def test_required_and_secret_rejection():
 with pytest.raises(ValueError): build_reconciliation(reconciliation_id="",execution_reference=ref("exec"),expected_state=LifecycleState.CREATED,observed_state=LifecycleState.CREATED,result_reference=None,evidence_references=(),trace_reference=ref("trace"))
 with pytest.raises(ValueError): build_reconciliation(reconciliation_id="r",execution_reference=ref("token=secret"),expected_state=LifecycleState.CREATED,observed_state=LifecycleState.CREATED,result_reference=None,evidence_references=(),trace_reference=ref("trace"))


