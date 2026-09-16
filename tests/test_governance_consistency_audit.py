from app.services.governance_consistency_audit import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def r(i='x',s=ReferenceStatus.VALID): return ReferenceToken(i,'sha256:'+i,s)
def a(**kw):
 d=dict(audit_id='a',baseline_reference=r('b'),closure_reference=r('c'),handoff_reference=r('h'),readiness_reference=r('r'),change_control_reference=r('cc'),consistency_findings=(),trace_reference=r('t')); d.update(kw); return GovernanceConsistencyAudit(**d)
def test_ok(): assert evaluate_consistency(a()) is ConsistencyOutcome.CONSISTENT
def test_warn(): assert evaluate_consistency(a(consistency_findings=('هشدار',))) is ConsistencyOutcome.CONSISTENT_WITH_WARNINGS
def test_block(): assert evaluate_consistency(a(baseline_reference=r('x',ReferenceStatus.BLOCKED))) is ConsistencyOutcome.BLOCKED
def test_invalid(): assert evaluate_consistency(a(closure_reference=r('x',ReferenceStatus.INVALID))) is ConsistencyOutcome.INCONSISTENT
def test_trace(): assert evaluate_consistency(a(trace_reference=r('x',ReferenceStatus.BLOCKED))) is ConsistencyOutcome.CONSISTENT_WITH_WARNINGS
def test_unknown(): assert evaluate_consistency(a(readiness_reference=r('x',ReferenceStatus.REQUIRES_REVIEW))) is ConsistencyOutcome.UNKNOWN
def test_digest():
 x=a(); object.__setattr__(x,'audit_digest','sha256:bad'); assert evaluate_consistency(x) is ConsistencyOutcome.INCONSISTENT
def test_order(): assert a(consistency_findings=('b','a')).consistency_findings==('a','b')
