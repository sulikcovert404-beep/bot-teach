from app.services.pre_execution_certification_master_package import *


def make(**o):
 d={k:("x",) for k in ('governance_closure_verification','authority_boundary_verification','readiness_chain_verification','state_consistency_verification','transition_assurance_verification','handoff_readiness','execution_architecture_review','safety_gate_review','restrictions','entry_conditions')}; d.update(certification_id='c',overall_posture='ready',blockers=(),trace_reference='t',certification_digest='d'); d.update(o); return PreExecutionCertificationMasterPackage(**d)
def test_certified(): assert make().outcome() is PreExecutionCertificationOutcome.PRE_EXECUTION_CERTIFIED
def test_warning_blocked(): assert make(blockers=('b',)).outcome() is PreExecutionCertificationOutcome.PRE_EXECUTION_CERTIFIED_WITH_WARNINGS; assert make(certification_digest='').outcome() is PreExecutionCertificationOutcome.PRE_EXECUTION_BLOCKED
def test_guard(): assert make(execution_permission=True).outcome() is PreExecutionCertificationOutcome.PRE_EXECUTION_NOT_CERTIFIED
