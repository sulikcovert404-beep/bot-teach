from app.services.baseline_change_control import *
from app.services.runtime_admission_bundle import ReferenceToken, ReferenceStatus

def r(name, status=ReferenceStatus.VALID): return ReferenceToken(name, 'a'*64, status)
def c(**kw):
 d=dict(change_request_id='c1',baseline_reference=r('baseline'),proposed_changes=('field',),impact_reference=r('impact'),version_transition_reference=r('compatible'),trace_reference=r('trace'))
 d.update(kw); return BaselineChangeControl(**d)
def test_allowed(): assert evaluate_change_control(c()) is ChangeOutcome.ALLOWED
def test_noop_allowed(): assert evaluate_change_control(c(proposed_changes=(),impact_reference=None,version_transition_reference=None)) is ChangeOutcome.ALLOWED
def test_reviewed(): assert evaluate_change_control(c(version_transition_reference=r('review-transition'))) is ChangeOutcome.ALLOWED_WITH_REVIEW
def test_rejected_incompatible(): assert evaluate_change_control(c(version_transition_reference=r('INCOMPATIBLE'))) is ChangeOutcome.REJECTED
def test_blocked_missing_evidence(): assert evaluate_change_control(c(impact_reference=None)) is ChangeOutcome.BLOCKED
def test_blocked_unknown_baseline(): assert evaluate_change_control(c(baseline_reference=r('b',ReferenceStatus.REQUIRES_REVIEW))) is ChangeOutcome.BLOCKED
def test_unknown_trace(): assert evaluate_change_control(c(trace_reference=r('t',ReferenceStatus.REQUIRES_REVIEW))) is ChangeOutcome.UNKNOWN
def test_digest_mismatch():
 x=c(); object.__setattr__(x,'decision_digest','sha256:'+'0'*64); assert evaluate_change_control(x) is ChangeOutcome.REJECTED
def test_deterministic_and_nfc():
 assert c(proposed_changes=('الف‌ب','x')).canonical_bytes()==c(proposed_changes=('x','الف‌ب')).canonical_bytes()
def test_secret_rejected():
 try: c(change_request_id='token')
 except ValueError: pass
 else: raise AssertionError
