"""Immutable, infrastructure-independent content integration assessment."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "CONTENT_INTEGRATION_READY"
    READY_WITH_WARNINGS = "CONTENT_INTEGRATION_READY_WITH_WARNINGS"
    DEFERRED = "CONTENT_INTEGRATION_DEFERRED"
    BLOCKED = "CONTENT_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class ContentIntegrationReadinessReview:
    storage_requirements: Tuple[str, ...] = ()
    data_lifecycle: Tuple[str, ...] = ()
    compatibility_impact: Tuple[str, ...] = ()
    ownership_model: Tuple[str, ...] = ()
    access_boundaries: Tuple[str, ...] = ()
    permission_requirements: Tuple[str, ...] = ()
    affected_modules: Tuple[str, ...] = ()
    contracts: Tuple[str, ...] = ()
    risks: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    integration_review_only: bool = True
    implementation_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.integration_review_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.runtime_execution, self.deployment,
                self.database_change, self.infrastructure_change, self.credential_change)):
            return Outcome.BLOCKED
        required = (self.storage_requirements, self.data_lifecycle,
                    self.compatibility_impact, self.ownership_model,
                    self.access_boundaries, self.permission_requirements,
                    self.affected_modules, self.contracts, self.risks, self.decision)
        if any(not value for value in required):
            return Outcome.DEFERRED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
