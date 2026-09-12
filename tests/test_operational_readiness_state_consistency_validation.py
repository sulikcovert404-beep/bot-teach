from app.services.operational_readiness_state_consistency_validation import *
def make(**k):
 d=dict(validation_id='v',state_model_reference='s',decision_framework_reference='d',review_framework_reference='r',assessment_reference='a',consistency_rules=('aligned',),transition_checks=('valid',),conflict_findings=(),validation_constraints=('pure',),scope_exclusions=('runtime',),boundary_assertions={'execution':False,'runtime_state':False},trace_reference='t',validation_digest='h'); d.update(k); return OperationalReadinessStateConsistencyValidation(**d)
def test_consistent(): assert make().outcome() is ConsistencyOutcome.STATE_CONSISTENT
def test_blocked(): assert make(trace_reference='').outcome() is ConsistencyOutcome.STATE_BLOCKED
def test_conflict(): assert make(conflict_findings=('conflict',)).outcome() is ConsistencyOutcome.STATE_INCONSISTENT
