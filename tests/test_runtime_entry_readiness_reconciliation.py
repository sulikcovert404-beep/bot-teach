from app.services.runtime_admission_bundle import ReferenceToken, ReferenceStatus
from app.services.runtime_entry_readiness_reconciliation import *
def ref(s=ReferenceStatus.VALID, text='x'): return ReferenceToken(text, 'sha256:abc', s)
def make(**kw):
 d=dict(preparation_review_reference=ref(),runtime_entry_decision_reference=ref(text='e'),readiness_snapshot_reference=ref(text='s'),environment_readiness_reference=ref(text='v'),trace_reference=ref(text='t')); d.update(kw); return RuntimeEntryReadinessReconciliation('r1',**d)
def test_aligned(): assert evaluate_runtime_entry_readiness_reconciliation(make()) is ReconciliationOutcome.ALIGNED
def test_warning_is_conflict_finding(): assert evaluate_runtime_entry_readiness_reconciliation(make(conflict_findings=({'code':'DRIFT'},))) is ReconciliationOutcome.CONFLICTED
def test_blocked(): assert evaluate_runtime_entry_readiness_reconciliation(make(preparation_review_reference=ref(ReferenceStatus.BLOCKED))) is ReconciliationOutcome.BLOCKED
def test_unknown(): assert evaluate_runtime_entry_readiness_reconciliation(make(environment_readiness_reference=ref(ReferenceStatus.REQUIRES_REVIEW))) is ReconciliationOutcome.UNKNOWN
def test_invalid_digest():
 r=make(); object.__setattr__(r,'reconciliation_digest','sha256:bad'); assert evaluate_runtime_entry_readiness_reconciliation(r) is ReconciliationOutcome.BLOCKED
def test_deterministic_persian():
 a=make(conflict_findings=({'message':'می\u200cشود'},)); b=make(conflict_findings=({'message':'می\u200cشود'},)); assert a.reconciliation_digest==b.reconciliation_digest
