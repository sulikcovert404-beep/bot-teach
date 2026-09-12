"""Immutable controlled-execution runbook design."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "RUNBOOK_READY"
    READY_WITH_WARNINGS = "RUNBOOK_READY_WITH_WARNINGS"
    INCOMPLETE = "RUNBOOK_INCOMPLETE"
    BLOCKED = "RUNBOOK_BLOCKED"


@dataclass(frozen=True)
class ControlledExecutionRunbookDesign:
    ordered_steps: Tuple[str, ...] = ()
    checkpoints: Tuple[str, ...] = ()
    stop_conditions: Tuple[str, ...] = ()
    rollback_triggers: Tuple[str, ...] = ()
    recovery_sequence: Tuple[str, ...] = ()
    post_rollback_validation: Tuple[str, ...] = ()
    execution_owner: str = ""
    approval_owner: str = ""
    incident_owner: str = ""
    pre_checks: Tuple[str, ...] = ()
    post_checks: Tuple[str, ...] = ()
    failure_handling: Tuple[str, ...] = ()
    planned_actions: Tuple[str, ...] = ()
    evidence_fields: Tuple[str, ...] = ()
    decision_points: Tuple[str, ...] = ()
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    runbook_design_only: bool = True
    execution_permission: bool = False
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.runbook_design_only:
            return Outcome.BLOCKED
        if any((self.execution_permission, self.production_execution, self.deployment,
                self.migration_execution, self.database_change, self.credential_change,
                self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.ordered_steps, self.checkpoints, self.stop_conditions,
                    self.rollback_triggers, self.recovery_sequence,
                    self.post_rollback_validation, self.execution_owner,
                    self.approval_owner, self.incident_owner, self.pre_checks,
                    self.post_checks, self.failure_handling, self.planned_actions,
                    self.evidence_fields, self.decision_points)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
