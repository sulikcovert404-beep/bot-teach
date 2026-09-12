"""Immutable authorization review for production enablement implementation."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "PRODUCTION_ENABLEMENT_READY"
    READY_WITH_WARNINGS = "PRODUCTION_ENABLEMENT_READY_WITH_WARNINGS"
    DEFERRED = "PRODUCTION_ENABLEMENT_DEFERRED"
    BLOCKED = "PRODUCTION_ENABLEMENT_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementImplementationAuthorizationReview:
    storage_design: Tuple[str, ...] = ()
    migration_design: Tuple[str, ...] = ()
    authorization_design: Tuple[str, ...] = ()
    activation_design: Tuple[str, ...] = ()
    data_risks: Tuple[str, ...] = ()
    security_risks: Tuple[str, ...] = ()
    operational_risks: Tuple[str, ...] = ()
    rollback_risks: Tuple[str, ...] = ()
    allowed_actions: Tuple[str, ...] = ()
    forbidden_actions: Tuple[str, ...] = ()
    phase_separation: Tuple[str, ...] = ()
    execution_ownership: str = ""
    approval_ownership: str = ""
    incident_ownership: str = ""
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
