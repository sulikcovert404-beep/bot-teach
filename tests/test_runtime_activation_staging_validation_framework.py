import pytest

from app.services.runtime_activation_staging_validation_framework import (
    RuntimeActivationStagingValidationFramework as F,
)
from app.services.runtime_activation_staging_validation_framework import (
    StagingValidationOutcome as O,
)


def make(**kw):
    d={"framework_id": "f1", "final_readiness_review_reference": "review:1", "assurance_bundle_reference": "bundle:1", "activation_decision_reference": "decision:1", "validation_plan_reference": "plan:1", "evidence_requirements": ("tests",), "rollback_requirements": ("restore",), "trace_reference": "trace:1"}
    d.update(kw); return F(**d)

def test_digest_and_immutability():
    f=make(); assert f.framework_digest == f.canonical_digest()
    with pytest.raises((AttributeError, TypeError)): f.framework_id="x"

def test_outcome_precedence():
    assert F.evaluate(references=("BLOCKED",)) is O.STAGING_VALIDATION_BLOCKED
    assert F.evaluate(references=("INVALID",), evidence=("x",), rollback=("y",)) is O.STAGING_VALIDATION_NOT_READY
    assert F.evaluate(references=("ok",)) is O.UNKNOWN
    assert F.evaluate(references=("ok",), evidence=("WARNING",), rollback=("y",)) is O.STAGING_VALIDATION_READY_WITH_WARNINGS
    assert F.evaluate(references=("ok",), evidence=("x",), rollback=("y",)) is O.STAGING_VALIDATION_READY

def test_tamper_and_secret_rejected():
    with pytest.raises(ValueError): make(framework_digest="bad")
    with pytest.raises(ValueError): make(trace_reference="secret=x")
