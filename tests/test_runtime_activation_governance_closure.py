
import pytest

from app.services.runtime_activation_governance_closure import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def make(**kw):
    r = ReferenceToken("ref", "sha256:x")
    values = {"activation_control_plane_reference": r, "activation_decision_reference": r, "activation_review_reference": r, "runtime_entry_consolidation_reference": r, "governance_freeze_reference": r, "baseline_manifest_reference": r, "trace_reference": r, "boundary_assertions": ("runtime_activation=PROHIBITED", "runtime_admission=PROHIBITED", "execution=false")}
    values.update(kw)
    return RuntimeActivationGovernanceClosure("c1", **values)

def test_closed_is_immutable_and_deterministic():
    c = make(); assert evaluate_runtime_activation_governance_closure(c) is GovernanceClosureOutcome.GOVERNANCE_CLOSED
    with pytest.raises((AttributeError, TypeError)): c.closure_id = "x"
    assert c.compute_digest() == c.closure_digest

def test_precedence_and_guards():
    r = ReferenceToken("ref", "sha256:x", ReferenceStatus.BLOCKED)
    assert evaluate_runtime_activation_governance_closure(make(activation_control_plane_reference=r)) is GovernanceClosureOutcome.GOVERNANCE_BLOCKED
    assert evaluate_runtime_activation_governance_closure(make(boundary_assertions=())) is GovernanceClosureOutcome.GOVERNANCE_OPEN

def test_tamper_and_secret_rejected():
    with pytest.raises(ValueError): make(closure_digest="sha256:bad")
    with pytest.raises(ValueError): make(consistency_findings=({"password": "x"},))
