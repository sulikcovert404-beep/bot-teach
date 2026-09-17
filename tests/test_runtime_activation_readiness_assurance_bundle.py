import pytest

from app.services.runtime_activation_readiness_assurance_bundle import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def make(**kw):
 r=ReferenceToken("ref","sha256:x"); vals={n:r for n in ("readiness_baseline_freeze_reference","governance_closure_reference","activation_control_plane_reference","activation_decision_reference","trace_reference")}; vals["evidence_references"]=(r,); vals.update(kw); return RuntimeActivationReadinessAssuranceBundle("b1",**vals)
def test_confirmed_digest_immutable():
 b=make(); assert evaluate_runtime_activation_readiness_assurance_bundle(b) is AssuranceOutcome.ASSURANCE_CONFIRMED; assert b.digest_matches()
 with pytest.raises((AttributeError,TypeError)): b.bundle_id="x"
def test_precedence():
 r=ReferenceToken("ref","sha256:x",ReferenceStatus.BLOCKED); assert evaluate_runtime_activation_readiness_assurance_bundle(make(evidence_references=(r,))) is AssuranceOutcome.ASSURANCE_BLOCKED
 assert evaluate_runtime_activation_readiness_assurance_bundle(make(assurance_findings=({"contradiction":"x"},))) is AssuranceOutcome.ASSURANCE_FAILED
def test_secret_tamper():
 with pytest.raises(ValueError): make(assurance_findings=({"token":"x"},))
 with pytest.raises(ValueError): make(assurance_digest="sha256:bad")
