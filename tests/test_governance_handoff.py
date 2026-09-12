from app.services.governance_handoff import *
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus

def r(i='x',s=ReferenceStatus.VALID): return ReferenceToken(i,'sha256:'+i,s)
def b(**kw):
 d=dict(handoff_id='h',baseline_reference=r('base'),closure_reference=r('close'),readiness_snapshot_reference=r('ready'),change_control_reference=r('change'),evidence_references=(r('evidence'),),trace_reference=r('trace')); d.update(kw); return GovernanceHandoffBundle(**d)
def test_accept(): assert evaluate_handoff(b()) is HandoffOutcome.ACCEPTED
def test_warn(): assert evaluate_handoff(b(change_control_reference=r('warn'))) is HandoffOutcome.ACCEPTED_WITH_WARNINGS
def test_block(): assert evaluate_handoff(b(),baseline_frozen=False) is HandoffOutcome.BLOCKED
def test_invalid(): assert evaluate_handoff(b(closure_reference=r('x',ReferenceStatus.INVALID))) is HandoffOutcome.REJECTED
def test_trace(): assert evaluate_handoff(b(trace_reference=r('x',ReferenceStatus.BLOCKED))) is HandoffOutcome.BLOCKED
def test_nfc(): assert b(handoff_id='ح‌').compute_digest()==b(handoff_id='ح‌').compute_digest()
