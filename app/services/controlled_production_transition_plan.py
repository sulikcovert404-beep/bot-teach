"""Immutable plan for a controlled production transition."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "TRANSITION_PLAN_READY"
    READY_WITH_WARNINGS = "TRANSITION_PLAN_READY_WITH_WARNINGS"
    BLOCKED = "TRANSITION_PLAN_BLOCKED"


@dataclass(frozen=True)
class ControlledProductionTransitionPlan:
    rollout_model: tuple[str, ...] = ()
    entry_criteria: tuple[str, ...] = ()
    exit_criteria: tuple[str, ...] = ()
    storage_migration: tuple[str, ...] = ()
    rollback_strategy: tuple[str, ...] = ()
    validation_checkpoints: tuple[str, ...] = ()
    identity_integration: tuple[str, ...] = ()
    permission_rollout: tuple[str, ...] = ()
    security_gates: tuple[str, ...] = ()
    monitoring: tuple[str, ...] = ()
    incident_handling: tuple[str, ...] = ()
    recovery_process: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    transition_planning_only: bool = True
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.transition_planning_only:
            return Outcome.BLOCKED
        if any((self.production_execution, self.deployment, self.migration_execution,
                self.database_change, self.credential_change, self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.rollout_model, self.entry_criteria, self.exit_criteria,
                    self.storage_migration, self.rollback_strategy,
                    self.validation_checkpoints, self.identity_integration,
                    self.permission_rollout, self.security_gates, self.monitoring,
                    self.incident_handling, self.recovery_process, self.decision)
        return Outcome.READY_WITH_WARNINGS if self.warnings and all(required) else Outcome.READY if all(required) else Outcome.BLOCKED
