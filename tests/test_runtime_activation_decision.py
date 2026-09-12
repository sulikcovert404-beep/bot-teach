import pytest
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus
from app.services.runtime_activation_decision import *
def ref(i="r",s=ReferenceStatus.VALID): return ReferenceToken(i,"sha256:"+i,s)
def dec(**kw):
 d=dict(decision_id="d1",activation_governance_review_reference=ref("gr"),activation_readiness_package_reference=ref("p"),runtime_entry_decision_reference=ref("e"),governance_freeze_reference=ref("g"),baseline_manifest_reference=ref("b"),change_control_reference=ref("c"),consistency_audit_reference=ref("a"),decision_reason="زنجیره معتبر است",trace_reference=ref("t"));d.update(kw);return RuntimeActivationDecision(**d)
def test_allowed_and_deterministic():
 d=dec();assert evaluate_runtime_activation_decision(d) is ActivationDecisionOutcome.ACTIVATION_ALLOWED;assert dec().canonical_bytes()==d.canonical_bytes();assert d.payload()["executable"] is False
def test_warning_and_blocked():
 assert evaluate_runtime_activation_decision(dec(decision_findings=({"message":"هشدار"},))) is ActivationDecisionOutcome.ACTIVATION_ALLOWED_WITH_WARNINGS
 assert evaluate_runtime_activation_decision(dec(governance_freeze_reference=ref("g",ReferenceStatus.BLOCKED))) is ActivationDecisionOutcome.ACTIVATION_BLOCKED
def test_denied_unknown_secret_tamper():
 assert evaluate_runtime_activation_decision(dec(runtime_entry_decision_reference=ref("e",ReferenceStatus.INVALID))) is ActivationDecisionOutcome.ACTIVATION_DENIED
 assert evaluate_runtime_activation_decision(dec(runtime_entry_decision_reference=ref("e",ReferenceStatus.REQUIRES_REVIEW))) is ActivationDecisionOutcome.UNKNOWN
 with pytest.raises(ValueError): dec(decision_reason="api_key=x")
 with pytest.raises(ValueError): dec(decision_digest="sha256:bad")
