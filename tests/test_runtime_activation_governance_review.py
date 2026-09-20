import pytest

from app.services.runtime_activation_governance_review import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def ref(i="r",s=ReferenceStatus.VALID): return ReferenceToken(i,"sha256:"+i,s)
def pkg(**kw):
 d={"review_id": "r1","activation_readiness_package_reference": ref("p"),"runtime_entry_decision_reference": ref("d"),"governance_freeze_reference": ref("g"),"baseline_manifest_reference": ref("b"),"change_control_reference": ref("c"),"consistency_audit_reference": ref("a"),"trace_reference": ref("t")};d.update(kw);return RuntimeActivationGovernanceReview(**d)
def test_valid_deterministic():
 r=pkg();assert evaluate_runtime_activation_governance_review(r) is ActivationGovernanceOutcome.APPROVED_FOR_ACTIVATION_REVIEW;assert pkg().canonical_bytes()==r.canonical_bytes()
def test_warning_and_precedence():
 assert evaluate_runtime_activation_governance_review(pkg(review_findings=({"message":"هشدار"},))) is ActivationGovernanceOutcome.APPROVED_WITH_WARNINGS
 assert evaluate_runtime_activation_governance_review(pkg(baseline_manifest_reference=ref("b",ReferenceStatus.BLOCKED))) is ActivationGovernanceOutcome.BLOCKED
def test_invalid_unknown_secret_and_tamper():
 assert evaluate_runtime_activation_governance_review(pkg(runtime_entry_decision_reference=ref("d",ReferenceStatus.INVALID))) is ActivationGovernanceOutcome.NOT_APPROVED
 assert evaluate_runtime_activation_governance_review(pkg(runtime_entry_decision_reference=ref("d",ReferenceStatus.REQUIRES_REVIEW))) is ActivationGovernanceOutcome.UNKNOWN
 with pytest.raises(ValueError): pkg(review_findings=({"token":"x"},))
 with pytest.raises(ValueError): pkg(review_digest="sha256:bad")
