"""Immutable plan for a controlled production transition."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "TRANSITION_PLAN_READY"
    READY_WITH_WARNINGS = "TRANSITION_PLAN_READY_WITH_WARNINGS"
    BLOCKED = "TRANSITION_PLAN_BLOCKED"


@dataclass(frozen=True)
class ControlledProductionTransitionPlan:
    rollout_model: Tuple[str, ...] = ()
    entry_criteria: Tuple[str, ...] = ()
    exit_criteria: Tuple[str, ...] = ()
    storage_migration: Tuple[str, ...] = ()
    rollback_strategy: Tuple[str, ...] = ()
    validation_checkpoints: Tuple[str, ...] = ()
    identity_integration: Tuple[str, ...] = ()
    permission_rollout: Tuple[str, ...] = ()
    security_gates: Tuple[str, ...] = ()
    monitoring: Tuple[str, ...] = ()
    incident_handling: Tuple[str, ...] = ()
    recovery_process: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
