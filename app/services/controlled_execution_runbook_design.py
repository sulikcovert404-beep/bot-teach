"""Immutable controlled-execution runbook design."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "RUNBOOK_READY"
    READY_WITH_WARNINGS = "RUNBOOK_READY_WITH_WARNINGS"
    INCOMPLETE = "RUNBOOK_INCOMPLETE"
    BLOCKED = "RUNBOOK_BLOCKED"


@dataclass(frozen=True)
class ControlledExecutionRunbookDesign:
    ordered_steps: tuple[str, ...] = ()
    checkpoints: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    rollback_triggers: tuple[str, ...] = ()
    recovery_sequence: tuple[str, ...] = ()
    post_rollback_validation: tuple[str, ...] = ()
    execution_owner: str = ""
    approval_owner: str = ""
    incident_owner: str = ""
    pre_checks: tuple[str, ...] = ()
    post_checks: tuple[str, ...] = ()
    failure_handling: tuple[str, ...] = ()
    planned_actions: tuple[str, ...] = ()
    evidence_fields: tuple[str, ...] = ()
    decision_points: tuple[str, ...] = ()
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
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
