from app.services.execution_governance_safety_gate_package import *
def make(**o):
 d={k:("x",) for k in ('execution_readiness_criteria','ownership_boundary','decision_checkpoints','safety_conditions','failure_boundaries','rollback_requirements','change_acceptance_semantics','validation_requirements','rejection_conditions','monitoring_prerequisites','escalation_readiness','control_ownership','forbidden_transitions')}; d.update(gate_id='g',unresolved_risks=(),blockers=(),trace_reference='t',gate_digest='d'); d.update(o); return ExecutionGovernanceSafetyGatePackage(**d)
def test_ready(): assert make().outcome() is ExecutionGateOutcome.EXECUTION_GATE_READY
def test_warning_blocked(): assert make(blockers=('b',)).outcome() is ExecutionGateOutcome.EXECUTION_GATE_READY_WITH_WARNINGS; assert make(gate_digest='').outcome() is ExecutionGateOutcome.EXECUTION_GATE_BLOCKED
def test_guard(): assert make(execution_permission=True).outcome() is ExecutionGateOutcome.EXECUTION_GATE_INCOMPLETE
