from app.services.operational_readiness_final_assurance import *
def make(**k):
 d=dict(assurance_id='a',state_consistency_validation_reference='v',state_model_reference='s',decision_framework_reference='d',review_framework_reference='r',governance_model_reference='g',evidence_model_reference='e',traceability_contract_reference='t',assurance_findings=(),assurance_constraints=('pure',),boundary_assertions={'execution':False,'runtime_state':False},trace_reference='tr',assurance_digest='h'); d.update(k); return OperationalReadinessFinalAssurance(**d)
def test_confirmed(): assert make().outcome() is AssuranceOutcome.ASSURANCE_CONFIRMED
def test_blocked(): assert make(assurance_digest='').outcome() is AssuranceOutcome.ASSURANCE_BLOCKED
def test_not_confirmed(): assert make(assurance_findings=('gap',)).outcome() is AssuranceOutcome.ASSURANCE_NOT_CONFIRMED
