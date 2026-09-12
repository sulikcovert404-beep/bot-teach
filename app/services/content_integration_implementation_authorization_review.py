"""Pure authorization assessment for content integration implementation."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "CONTENT_INTEGRATION_IMPLEMENTATION_READY"
    READY_WITH_WARNINGS = "CONTENT_INTEGRATION_READY_WITH_WARNINGS"
    BLOCKED = "CONTENT_INTEGRATION_BLOCKED"
    DEFERRED = "CONTENT_INTEGRATION_DEFERRED"


@dataclass(frozen=True)
class ContentIntegrationImplementationAuthorizationReview:
    persistence_design: Tuple[str, ...] = ()
    authorization_design: Tuple[str, ...] = ()
    contracts: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    required_changes: Tuple[str, ...] = ()
    migration_requirements: Tuple[str, ...] = ()
    data_risks: Tuple[str, ...] = ()
    security_risks: Tuple[str, ...] = ()
    compatibility_risks: Tuple[str, ...] = ()
    allowed_changes: Tuple[str, ...] = ()
    forbidden_changes: Tuple[str, ...] = ()
    rollback_requirements: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
