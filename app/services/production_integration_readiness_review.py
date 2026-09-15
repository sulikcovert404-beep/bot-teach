"""Immutable readiness review for production integration composition."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "PRODUCTION_INTEGRATION_READY"
    READY_WITH_WARNINGS = "PRODUCTION_INTEGRATION_READY_WITH_WARNINGS"
    DEFERRED = "PRODUCTION_INTEGRATION_DEFERRED"
    BLOCKED = "PRODUCTION_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class ProductionIntegrationReadinessReview:
    data_ownership: tuple[str, ...] = ()
    access_enforcement: tuple[str, ...] = ()
    lifecycle_consistency: tuple[str, ...] = ()
    execution_sequence: tuple[str, ...] = ()
    prerequisite_chain: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    ownership_risks: tuple[str, ...] = ()
    permission_risks: tuple[str, ...] = ()
    data_integrity_risks: tuple[str, ...] = ()
    monitoring: tuple[str, ...] = ()
    incident_handling: tuple[str, ...] = ()
    recovery: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    integration_readiness_review_only: bool = True
    implementation_execution: bool = False
    credential_change: bool = False
    permission_change: bool = False
    database_change: bool = False
    migration_execution: bool = False
    runtime_activation: bool = False
    deployment: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.integration_readiness_review_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.credential_change,
                self.permission_change, self.database_change,
                self.migration_execution, self.runtime_activation, self.deployment)):
            return Outcome.BLOCKED
        required = (self.data_ownership, self.access_enforcement,
                    self.lifecycle_consistency, self.execution_sequence,
                    self.prerequisite_chain, self.ownership_risks,
                    self.permission_risks, self.data_integrity_risks,
                    self.monitoring, self.incident_handling, self.recovery,
                    self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        if self.blockers:
            return Outcome.BLOCKED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
