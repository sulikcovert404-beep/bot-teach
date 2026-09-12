"""Pure design contract for a future operational control plane."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "CONTROL_PLANE_READY"
    READY_WITH_WARNINGS = "CONTROL_PLANE_READY_WITH_WARNINGS"
    INCOMPLETE = "CONTROL_PLANE_INCOMPLETE"
    BLOCKED = "CONTROL_PLANE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OperationalControlPlaneFoundation:
    control_architecture: Tuple[str, ...] = ()
    policy_evaluation_semantics: Tuple[str, ...] = ()
    command_ownership: Tuple[str, ...] = ()
    workflow_boundaries: Tuple[str, ...] = ()
    escalation_model: Tuple[str, ...] = ()
    audit_boundary: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    trace_reference: str = ""
    control_plane_design_only: bool = True
    runtime_control: bool = False
    command_execution: bool = False
    runtime_activation: bool = False
    runtime_admission: bool = False
    execution: bool = False
    deployment: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.control_plane_design_only:
            return Outcome.INCOMPLETE
        if any((self.runtime_control, self.command_execution, self.runtime_activation,
                self.runtime_admission, self.execution, self.deployment,
                self.infrastructure_change)):
            return Outcome.INCOMPLETE
        required = (self.control_architecture, self.policy_evaluation_semantics,
                    self.command_ownership, self.workflow_boundaries,
                    self.escalation_model, self.audit_boundary)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return (Outcome.READY_WITH_WARNINGS if self.blockers else Outcome.READY)
