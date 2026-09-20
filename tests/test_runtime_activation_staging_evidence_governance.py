import pytest

from app.services.runtime_activation_staging_evidence_governance import (
 EvidenceGovernanceOutcome as O,
)
from app.services.runtime_activation_staging_evidence_governance import (
 RuntimeActivationStagingEvidenceGovernance as G,
)


def make(**k):
 d={"governance_id": "g1","staging_validation_framework_reference": "framework:1","final_readiness_review_reference": "review:1","activation_decision_reference": "decision:1","evidence_requirements": ("logs",),"evidence_ownership": ("ops",),"validation_rules": ("hash",),"trace_reference": "trace:1"}; d.update(k); return G(**d)
def test_digest_immutable():
 g=make(); assert g.governance_digest==g.canonical_digest()
 with pytest.raises((AttributeError,TypeError)): g.governance_id="x"
def test_outcomes():
 assert G.evaluate(references=("BLOCKED",)) is O.EVIDENCE_GOVERNANCE_BLOCKED
 assert G.evaluate(references=("INVALID",),requirements=("x",),ownership=("x",),rules=("x",)) is O.EVIDENCE_GOVERNANCE_NOT_READY
 assert G.evaluate(references=("ok",)) is O.UNKNOWN
 assert G.evaluate(references=("ok",),requirements=("WARNING",),ownership=("x",),rules=("x",)) is O.EVIDENCE_GOVERNANCE_READY_WITH_WARNINGS
 assert G.evaluate(references=("ok",),requirements=("x",),ownership=("x",),rules=("x",)) is O.EVIDENCE_GOVERNANCE_READY
def test_rejects_tamper_and_secret():
 with pytest.raises(ValueError): make(governance_digest="bad")
 with pytest.raises(ValueError): make(trace_reference="secret=x")
