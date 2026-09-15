"""Pure authorization assessment for content integration implementation."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "CONTENT_INTEGRATION_IMPLEMENTATION_READY"
    READY_WITH_WARNINGS = "CONTENT_INTEGRATION_READY_WITH_WARNINGS"
    BLOCKED = "CONTENT_INTEGRATION_BLOCKED"
    DEFERRED = "CONTENT_INTEGRATION_DEFERRED"


@dataclass(frozen=True)
class ContentIntegrationImplementationAuthorizationReview:
    persistence_design: tuple[str, ...] = ()
    authorization_design: tuple[str, ...] = ()
    contracts: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    required_changes: tuple[str, ...] = ()
    migration_requirements: tuple[str, ...] = ()
    data_risks: tuple[str, ...] = ()
    security_risks: tuple[str, ...] = ()
    compatibility_risks: tuple[str, ...] = ()
    allowed_changes: tuple[str, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    rollback_requirements: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    integration_authorization_review_only: bool = True
    implementation_permission: bool = False
    database_change: bool = False
    migration_execution: bool = False
    authorization_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.integration_authorization_review_only:
            return Outcome.BLOCKED
        if any((self.implementation_permission, self.database_change,
                self.migration_execution, self.authorization_execution,
                self.runtime_execution, self.deployment)):
            return Outcome.BLOCKED
        required = (self.persistence_design, self.authorization_design, self.contracts,
                    self.dependencies, self.required_changes, self.migration_requirements,
                    self.data_risks, self.security_risks, self.compatibility_risks,
                    self.allowed_changes, self.forbidden_changes,
                    self.rollback_requirements, self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
