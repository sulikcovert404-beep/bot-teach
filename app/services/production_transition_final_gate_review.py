"""Immutable final gate review before any production transition execution."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    APPROVED = "TRANSITION_APPROVED_FOR_EXECUTION_REVIEW"
    APPROVED_WITH_CONDITIONS = "TRANSITION_APPROVED_WITH_CONDITIONS"
    DEFERRED = "TRANSITION_DEFERRED"
    BLOCKED = "TRANSITION_BLOCKED"


@dataclass(frozen=True)
class ProductionTransitionFinalGateReview:
    transition_plan: tuple[str, ...] = ()
    rollback_plan: tuple[str, ...] = ()
    validation_plan: tuple[str, ...] = ()
    remaining_risks: tuple[str, ...] = ()
    deferred_items: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    authorization_readiness: tuple[str, ...] = ()
    identity_boundaries: tuple[str, ...] = ()
    credential_impact: tuple[str, ...] = ()
    monitoring_readiness: tuple[str, ...] = ()
    incident_response: tuple[str, ...] = ()
    recovery_readiness: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: tuple[str, ...] = ()
    final_gate_review_only: bool = True
    production_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    migration_execution: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.final_gate_review_only:
            return Outcome.BLOCKED
        if any((self.production_execution, self.deployment, self.database_change,
                self.migration_execution, self.credential_change, self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.transition_plan, self.rollback_plan, self.validation_plan,
                    self.deferred_items, self.authorization_readiness,
                    self.identity_boundaries, self.credential_impact,
                    self.monitoring_readiness, self.incident_response,
                    self.recovery_readiness, self.decision)
        if any(not value for value in required):
            return Outcome.DEFERRED
        if self.blockers:
            return Outcome.BLOCKED
        return Outcome.APPROVED_WITH_CONDITIONS if self.conditions or self.remaining_risks else Outcome.APPROVED
