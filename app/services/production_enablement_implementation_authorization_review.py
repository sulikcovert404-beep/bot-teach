"""Immutable authorization review for production enablement implementation."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "PRODUCTION_ENABLEMENT_READY"
    READY_WITH_WARNINGS = "PRODUCTION_ENABLEMENT_READY_WITH_WARNINGS"
    DEFERRED = "PRODUCTION_ENABLEMENT_DEFERRED"
    BLOCKED = "PRODUCTION_ENABLEMENT_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementImplementationAuthorizationReview:
    storage_design: tuple[str, ...] = ()
    migration_design: tuple[str, ...] = ()
    authorization_design: tuple[str, ...] = ()
    activation_design: tuple[str, ...] = ()
    data_risks: tuple[str, ...] = ()
    security_risks: tuple[str, ...] = ()
    operational_risks: tuple[str, ...] = ()
    rollback_risks: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    phase_separation: tuple[str, ...] = ()
    execution_ownership: str = ""
    approval_ownership: str = ""
    incident_ownership: str = ""
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    production_enablement_authorization_review_only: bool = True
    implementation_permission: bool = False
    migration_execution: bool = False
    database_change: bool = False
    deployment: bool = False
    runtime_activation: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.production_enablement_authorization_review_only:
            return Outcome.BLOCKED
        if any((self.implementation_permission, self.migration_execution,
                self.database_change, self.deployment, self.runtime_activation,
                self.credential_change)):
            return Outcome.BLOCKED
        required = (self.storage_design, self.migration_design,
                    self.authorization_design, self.activation_design,
                    self.data_risks, self.security_risks, self.operational_risks,
                    self.rollback_risks, self.allowed_actions, self.forbidden_actions,
                    self.phase_separation, self.execution_ownership,
                    self.approval_ownership, self.incident_ownership, self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
