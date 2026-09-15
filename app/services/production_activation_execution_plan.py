"""Controlled activation execution plan; planning only, with hard safety guards."""
from dataclasses import dataclass
from enum import StrEnum


class ActivationPlanOutcome(StrEnum):
    READY = "ACTIVATION_PLAN_READY"
    READY_WITH_WARNINGS = "ACTIVATION_PLAN_READY_WITH_WARNINGS"
    DEFERRED = "ACTIVATION_PLAN_DEFERRED"
    BLOCKED = "ACTIVATION_PLAN_BLOCKED"


@dataclass(frozen=True)
class ActivationExecutionPlan:
    activation_sequence: tuple[str, ...] = ()
    dependency_order: tuple[str, ...] = ()
    checkpoints: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    migration_steps: tuple[str, ...] = ()
    validation_checkpoints: tuple[str, ...] = ()
    rollback_points: tuple[str, ...] = ()
    identity_rollout: tuple[str, ...] = ()
    credential_handling: tuple[str, ...] = ()
    security_checks: tuple[str, ...] = ()
    execution_record_template: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    activation_execution_plan_only: bool = True
    runtime_activation: bool = False
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    identity_provider_change: bool = False

    def outcome(self) -> ActivationPlanOutcome:
        if not self.activation_execution_plan_only or not self.trace_reference:
            return ActivationPlanOutcome.BLOCKED
        if any((self.runtime_activation, self.production_execution, self.deployment,
                self.migration_execution, self.database_change,
                self.credential_change, self.identity_provider_change)):
            return ActivationPlanOutcome.BLOCKED
        required = (
            self.activation_sequence, self.dependency_order, self.checkpoints,
            self.allowed_actions, self.forbidden_actions, self.stop_conditions,
            self.migration_steps, self.validation_checkpoints, self.rollback_points,
            self.identity_rollout, self.credential_handling, self.security_checks,
            self.execution_record_template, self.decision,
        )
        if any(not value for value in required):
            return ActivationPlanOutcome.DEFERRED
        return (ActivationPlanOutcome.READY_WITH_WARNINGS
                if self.warnings else ActivationPlanOutcome.READY)
