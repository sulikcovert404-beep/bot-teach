import pytest

from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.runtime_entry_activation_readiness_package import *


def ref(i="r", s=ReferenceStatus.VALID): return ReferenceToken(i, "sha256:"+i, s)
def pkg(**kw):
 d={"package_id": "p1", "governance_consolidation_reference": ref("g"), "readiness_gate_reference": ref("g2"), "runtime_entry_decision_reference": ref("d"), "preparation_handoff_reference": ref("h"), "preparation_snapshot_reference": ref("s"), "readiness_reconciliation_reference": ref("rr"), "environment_readiness_reference": ref("e"), "evidence_references": (ref("x"),), "trace_reference": ref("t")}; d.update(kw); return RuntimeEntryActivationReadinessPackage(**d)
def test_ready_and_deterministic():
 p=pkg(); assert evaluate_runtime_entry_activation_readiness(p) is ActivationReadinessOutcome.READY_FOR_ACTIVATION_REVIEW; assert p.digest_matches(); assert p.canonical_bytes()==pkg().canonical_bytes()
def test_warning_and_blocked():
 assert evaluate_runtime_entry_activation_readiness(pkg(activation_findings=({"message":"هشدار"},))) is ActivationReadinessOutcome.READY_WITH_WARNINGS
 assert evaluate_runtime_entry_activation_readiness(pkg(evidence_references=(ref("x", ReferenceStatus.BLOCKED),))) is ActivationReadinessOutcome.BLOCKED
def test_invalid_unknown_and_secret():
 assert evaluate_runtime_entry_activation_readiness(pkg(runtime_entry_decision_reference=ref("d", ReferenceStatus.INVALID))) is ActivationReadinessOutcome.NOT_READY
 assert evaluate_runtime_entry_activation_readiness(pkg(runtime_entry_decision_reference=ref("d", ReferenceStatus.REQUIRES_REVIEW))) is ActivationReadinessOutcome.UNKNOWN
 with pytest.raises(ValueError): pkg(activation_findings=({"api_key":"x"},))
def test_digest_mismatch():
 with pytest.raises(ValueError): pkg(package_digest="sha256:bad")
