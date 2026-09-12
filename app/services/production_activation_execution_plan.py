"""Controlled activation execution plan; planning only, with hard safety guards."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Tuple


class ActivationPlanOutcome(StrEnum):
    READY = "ACTIVATION_PLAN_READY"
    READY_WITH_WARNINGS = "ACTIVATION_PLAN_READY_WITH_WARNINGS"
    DEFERRED = "ACTIVATION_PLAN_DEFERRED"
    BLOCKED = "ACTIVATION_PLAN_BLOCKED"


@dataclass(frozen=True)
class ActivationExecutionPlan:
    activation_sequence: Tuple[str, ...] = ()
    dependency_order: Tuple[str, ...] = ()
    checkpoints: Tuple[str, ...] = ()
    allowed_actions: Tuple[str, ...] = ()
    forbidden_actions: Tuple[str, ...] = ()
    stop_conditions: Tuple[str, ...] = ()
    migration_steps: Tuple[str, ...] = ()
    validation_checkpoints: Tuple[str, ...] = ()
    rollback_points: Tuple[str, ...] = ()
    identity_rollout: Tuple[str, ...] = ()
    credential_handling: Tuple[str, ...] = ()
    security_checks: Tuple[str, ...] = ()
    execution_record_template: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
