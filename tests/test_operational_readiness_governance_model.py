from app.services.operational_readiness_governance_model import (
 GovernanceOutcome,
 OperationalReadinessGovernanceModel,
)


def make(**k):
 d=dict(governance_id='g',assessment_framework_reference='a',governance_roles={'owner':'admin'},decision_boundaries=('design-only',),review_requirements=('peer',),evidence_requirements=('trace',),escalation_rules=('commander',),scope_exclusions=('runtime',),boundary_assertions={'runtime_activation':'PROHIBITED','execution':False},trace_reference='t',governance_digest='d'); d.update(k); return OperationalReadinessGovernanceModel(**d)
def test_defined(): assert make().outcome() is GovernanceOutcome.GOVERNANCE_DEFINED
def test_blocked(): assert make(governance_digest='').outcome() is GovernanceOutcome.GOVERNANCE_BLOCKED
def test_incomplete(): assert make(governance_roles={}).outcome() is GovernanceOutcome.GOVERNANCE_INCOMPLETE
