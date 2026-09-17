from app.services.operational_readiness_decision_framework import *


def make(**k):
 d=dict(decision_framework_id='d',governance_model_reference='g',assessment_framework_reference='a',evidence_model_reference='e',traceability_contract_reference='t',decision_rules=('r',),precedence_rules=('p',),decision_constraints=('c',),scope_exclusions=('runtime',),boundary_assertions={'permission_generation':False,'execution':False},trace_reference='tr',decision_digest='h'); d.update(k); return OperationalReadinessDecisionFramework(**d)
def test_defined(): assert make().outcome() is DecisionOutcome.DECISION_FRAMEWORK_DEFINED
def test_blocked(): assert make(decision_digest='').outcome() is DecisionOutcome.DECISION_FRAMEWORK_BLOCKED
def test_incomplete(): assert make(precedence_rules=()).outcome() is DecisionOutcome.DECISION_FRAMEWORK_INCOMPLETE
