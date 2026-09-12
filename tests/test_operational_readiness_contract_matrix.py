from app.services.operational_readiness_contract_matrix import *
def make(**k):
 d=dict(matrix_id='m',operational_design_foundation_reference='f',capability_inventory=('c',),dependency_matrix={'c':('d',)},control_requirements=('x',),risk_matrix={},scope_exclusions=('runtime',),transition_constraints=('approval',),boundary_assertions={'runtime_activation':'PROHIBITED','execution':False},trace_reference='t',matrix_digest='h'); d.update(k); return OperationalReadinessContractMatrix(**d)
def test_ready(): assert make().outcome() is MatrixOutcome.MATRIX_READY
def test_blocked(): assert make(matrix_digest='').outcome() is MatrixOutcome.MATRIX_BLOCKED
def test_incomplete(): assert make(capability_inventory=()).outcome() is MatrixOutcome.MATRIX_INCOMPLETE
