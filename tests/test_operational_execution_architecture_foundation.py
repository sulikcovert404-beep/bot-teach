from app.services.operational_execution_architecture_foundation import *
def make(**o):
 d={k:("x",) for k in ('component_boundaries','responsibility_separation','control_interfaces','safety_boundaries','failure_isolation','rollback_integration','control_plane_responsibilities','monitoring_design_semantics','escalation_model','change_stages','validation_sequence','recovery_points','governance_bridge')}; d.update(architecture_id='a',unresolved_risks=(),trace_reference='t',architecture_digest='d'); d.update(o); return OperationalExecutionArchitectureFoundation(**d)
def test_defined(): assert make().outcome() is ExecutionArchitectureOutcome.EXECUTION_ARCHITECTURE_DEFINED
def test_warning_blocked(): assert make(unresolved_risks=('r',)).outcome() is ExecutionArchitectureOutcome.EXECUTION_ARCHITECTURE_DEFINED_WITH_WARNINGS; assert make(architecture_digest='').outcome() is ExecutionArchitectureOutcome.EXECUTION_ARCHITECTURE_BLOCKED
def test_guard(): assert make(execution=True).outcome() is ExecutionArchitectureOutcome.EXECUTION_ARCHITECTURE_INCOMPLETE
