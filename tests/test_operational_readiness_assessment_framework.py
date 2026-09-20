from app.services.operational_readiness_assessment_framework import (
    AssessmentOutcome,
    OperationalReadinessAssessmentFramework,
)


def make(**overrides):
    d={'assessment_id': 'a', 'contract_matrix_reference': 'm', 'capability_assessments': {'c':'ready'}, 'dependency_findings': ('ok',), 'readiness_gaps': (), 'risk_summary': (), 'assessment_constraints': ('approval',), 'boundary_assertions': {'runtime_activation':'PROHIBITED','execution':False}, 'trace_reference': 't', 'assessment_digest': 'd'}
    d.update(overrides); return OperationalReadinessAssessmentFramework(**d)

def test_ready(): assert make().outcome() is AssessmentOutcome.ASSESSMENT_READY
def test_blocked_without_reference(): assert make(contract_matrix_reference='').outcome() is AssessmentOutcome.ASSESSMENT_BLOCKED
def test_gap_not_ready(): assert make(readiness_gaps=('missing control',)).outcome() is AssessmentOutcome.ASSESSMENT_NOT_READY
