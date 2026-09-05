"""Final pre-activation gate; review-only and non-authoritative."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Tuple


class ActivationOutcome(StrEnum):
    APPROVED = "ACTIVATION_APPROVED"
    APPROVED_WITH_CONDITIONS = "ACTIVATION_APPROVED_WITH_CONDITIONS"
    DEFERRED = "ACTIVATION_DEFERRED"
    BLOCKED = "ACTIVATION_BLOCKED"


@dataclass(frozen=True)
class FinalActivationGateReview:
    foundation_status: Tuple[str, ...] = ()
    authorization_status: Tuple[str, ...] = ()
    operational_readiness: Tuple[str, ...] = ()
    activation_scope: Tuple[str, ...] = ()
    allowed_actions: Tuple[str, ...] = ()
    forbidden_actions: Tuple[str, ...] = ()
    identity_readiness: Tuple[str, ...] = ()
    credential_boundary: Tuple[str, ...] = ()
    secret_handling: Tuple[str, ...] = ()
    monitoring: Tuple[str, ...] = ()
    incident_response: Tuple[str, ...] = ()
    rollback_readiness: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: Tuple[str, ...] = ()
    final_activation_gate_review_only: bool = True
    runtime_activation: bool = False
    production_execution: bool = False
    deployment: bool = False
    credential_change: bool = False
    identity_provider_change: bool = False
    database_change: bool = False
    migration_execution: bool = False

    def outcome(self) -> ActivationOutcome:
        if not self.final_activation_gate_review_only or not self.trace_reference:
            return ActivationOutcome.BLOCKED
        if any((self.runtime_activation, self.production_execution, self.deployment,
                self.credential_change, self.identity_provider_change,
                self.database_change, self.migration_execution)):
            return ActivationOutcome.BLOCKED
        required = (
            self.foundation_status, self.authorization_status,
            self.operational_readiness, self.activation_scope, self.allowed_actions,
            self.forbidden_actions, self.identity_readiness, self.credential_boundary,
            self.secret_handling, self.monitoring, self.incident_response,
            self.rollback_readiness, self.decision,
        )
        if any(not value for value in required):
            return ActivationOutcome.DEFERRED
        return (ActivationOutcome.APPROVED_WITH_CONDITIONS
                if self.conditions else ActivationOutcome.APPROVED)
