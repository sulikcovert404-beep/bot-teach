import pytest

from app.services.runtime_activation_staging_validation_assurance import AssuranceOutcome as O
from app.services.runtime_activation_staging_validation_assurance import (
 RuntimeActivationStagingValidationAssurance as A,
)


def make(**k):
 d=dict(assurance_id='a1',staging_validation_framework_reference='f:1',staging_evidence_governance_reference='g:1',final_readiness_review_reference='r:1',activation_decision_reference='d:1',readiness_baseline_freeze_reference='b:1',assurance_findings=(),trace_reference='t:1'); d.update(k); return A(**d)
def test_digest(): assert make().assurance_digest==make().canonical_digest()
def test_outcomes():
 assert A.evaluate(references=('BLOCKED',)) is O.ASSURANCE_BLOCKED; assert A.evaluate(references=('INVALID',)) is O.ASSURANCE_NOT_READY; assert A.evaluate(references=('UNKNOWN',)) is O.UNKNOWN; assert A.evaluate(references=('ok',),findings=('warn',)) is O.ASSURANCE_READY_WITH_WARNINGS; assert A.evaluate(references=('ok',)) is O.ASSURANCE_READY
def test_reject():
 with pytest.raises(ValueError): make(assurance_digest='bad')
 with pytest.raises(ValueError): make(trace_reference='secret=x')
