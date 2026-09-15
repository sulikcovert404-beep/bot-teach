"""Immutable governance and safety gate evidence; no execution authority."""
from dataclasses import dataclass
from enum import Enum
class ExecutionGateOutcome(str,Enum):
 EXECUTION_GATE_READY="EXECUTION_GATE_READY"; EXECUTION_GATE_READY_WITH_WARNINGS="EXECUTION_GATE_READY_WITH_WARNINGS"; EXECUTION_GATE_INCOMPLETE="EXECUTION_GATE_INCOMPLETE"; EXECUTION_GATE_BLOCKED="EXECUTION_GATE_BLOCKED"; UNKNOWN="UNKNOWN"
@dataclass(frozen=True)
class ExecutionGovernanceSafetyGatePackage:
 gate_id:str; execution_readiness_criteria:tuple[str,...]; ownership_boundary:tuple[str,...]; decision_checkpoints:tuple[str,...]; safety_conditions:tuple[str,...]; failure_boundaries:tuple[str,...]; rollback_requirements:tuple[str,...]; change_acceptance_semantics:tuple[str,...]; validation_requirements:tuple[str,...]; rejection_conditions:tuple[str,...]; monitoring_prerequisites:tuple[str,...]; escalation_readiness:tuple[str,...]; control_ownership:tuple[str,...]; unresolved_risks:tuple[str,...]; blockers:tuple[str,...]; forbidden_transitions:tuple[str,...]; trace_reference:str; gate_digest:str; execution_gate_only:bool=True; execution_permission:bool=False; runtime_activation:bool=False; runtime_admission:bool=False; execution:bool=False; deployment:bool=False
 def outcome(self)->ExecutionGateOutcome:
  if not all((self.gate_id,self.trace_reference,self.gate_digest)): return ExecutionGateOutcome.EXECUTION_GATE_BLOCKED
  if not self.execution_gate_only or self.execution_permission or self.runtime_activation or self.runtime_admission or self.execution or self.deployment: return ExecutionGateOutcome.EXECUTION_GATE_INCOMPLETE
  groups=(self.execution_readiness_criteria,self.ownership_boundary,self.decision_checkpoints,self.safety_conditions,self.failure_boundaries,self.rollback_requirements,self.change_acceptance_semantics,self.validation_requirements,self.rejection_conditions,self.monitoring_prerequisites,self.escalation_readiness,self.control_ownership,self.forbidden_transitions)
  if any(not g for g in groups): return ExecutionGateOutcome.EXECUTION_GATE_INCOMPLETE
  return ExecutionGateOutcome.EXECUTION_GATE_READY_WITH_WARNINGS if (self.unresolved_risks or self.blockers) else ExecutionGateOutcome.EXECUTION_GATE_READY
