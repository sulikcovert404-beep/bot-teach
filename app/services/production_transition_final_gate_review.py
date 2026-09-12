"""Immutable final gate review before any production transition execution."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    APPROVED = "TRANSITION_APPROVED_FOR_EXECUTION_REVIEW"
    APPROVED_WITH_CONDITIONS = "TRANSITION_APPROVED_WITH_CONDITIONS"
    DEFERRED = "TRANSITION_DEFERRED"
    BLOCKED = "TRANSITION_BLOCKED"


@dataclass(frozen=True)
class ProductionTransitionFinalGateReview:
    transition_plan: Tuple[str, ...] = ()
    rollback_plan: Tuple[str, ...] = ()
    validation_plan: Tuple[str, ...] = ()
    remaining_risks: Tuple[str, ...] = ()
    deferred_items: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    authorization_readiness: Tuple[str, ...] = ()
    identity_boundaries: Tuple[str, ...] = ()
    credential_impact: Tuple[str, ...] = ()
    monitoring_readiness: Tuple[str, ...] = ()
    incident_response: Tuple[str, ...] = ()
    recovery_readiness: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: Tuple[str, ...] = ()
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
