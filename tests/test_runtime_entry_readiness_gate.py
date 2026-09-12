from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.runtime_entry_readiness_gate import *
def r(n, s=ReferenceStatus.VALID): return ReferenceToken(n, "sha256:"+n, s)
def make(**kw):
 d={n:r(n) for n in ("governance_consolidation_reference","runtime_entry_decision_reference","readiness_reconciliation_reference","environment_readiness_reference","trace_reference")}; d.update(kw); return RuntimeEntryReadinessGate("g1",**d)
def test_outcomes():
 assert evaluate_runtime_entry_readiness_gate(make()) is ReadinessGateOutcome.READY
 assert evaluate_runtime_entry_readiness_gate(make(gate_findings=({"code":"WARN"},))) is ReadinessGateOutcome.READY_WITH_WARNINGS
 assert evaluate_runtime_entry_readiness_gate(make(governance_consolidation_reference=r("x",ReferenceStatus.BLOCKED))) is ReadinessGateOutcome.BLOCKED
 assert evaluate_runtime_entry_readiness_gate(make(governance_consolidation_reference=r("x",ReferenceStatus.INVALID))) is ReadinessGateOutcome.NOT_READY
 assert evaluate_runtime_entry_readiness_gate(make(governance_consolidation_reference=r("x",ReferenceStatus.REQUIRES_REVIEW))) is ReadinessGateOutcome.UNKNOWN
def test_integrity_and_persian():
 g=make(); assert g.digest_matches() and make().canonical_bytes()==g.canonical_bytes(); object.__setattr__(g,"gate_digest","sha256:bad"); assert evaluate_runtime_entry_readiness_gate(g) is ReadinessGateOutcome.BLOCKED
def test_non_authoritative(): assert make().payload()["runtime_admission"]=="PROHIBITED" and make().payload()["executable"] is False
