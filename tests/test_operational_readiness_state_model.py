from app.services.operational_readiness_state_model import *
def make(**k):
 d=dict(state_model_id='s',decision_framework_reference='d',decision_review_reference='r',assessment_reference='a',state_definitions={'READY':'readiness only'},state_transition_rules=('reviewed',),state_constraints=('non-runtime',),scope_exclusions=('runtime',),boundary_assertions={'runtime_state':False,'activation_state':False,'permission_state':False},trace_reference='t',state_digest='h'); d.update(k); return OperationalReadinessStateModel(**d)
def test_defined(): assert make().outcome() is StateOutcome.STATE_MODEL_DEFINED
def test_blocked(): assert make(state_digest='').outcome() is StateOutcome.STATE_MODEL_BLOCKED
def test_incomplete(): assert make(state_definitions={}).outcome() is StateOutcome.STATE_MODEL_INCOMPLETE
