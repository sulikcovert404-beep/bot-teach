"""Immutable production-readiness assessment; no production side effects."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "PRODUCTION_READY"
    READY_WITH_WARNINGS = "PRODUCTION_READY_WITH_WARNINGS"
    PREPARATION_REQUIRED = "PRODUCTION_PREPARATION_REQUIRED"
    BLOCKED = "PRODUCTION_BLOCKED"


@dataclass(frozen=True)
class ProductionReadinessAssessment:
    storage_options: tuple[str, ...] = ()
    durability_requirements: tuple[str, ...] = ()
    migration_readiness: tuple[str, ...] = ()
    identity_boundary: tuple[str, ...] = ()
    permission_architecture: tuple[str, ...] = ()
    security_requirements: tuple[str, ...] = ()
    monitoring_needs: tuple[str, ...] = ()
    failure_handling: tuple[str, ...] = ()
    rollback_requirements: tuple[str, ...] = ()
    critical_blockers: tuple[str, ...] = ()
    deferred_items: tuple[str, ...] = ()
    implementation_order: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    production_readiness_review_only: bool = True
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.production_readiness_review_only:
            return Outcome.BLOCKED
        if any((self.production_execution, self.deployment, self.migration_execution,
                self.database_change, self.credential_change, self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.storage_options, self.durability_requirements,
                    self.migration_readiness, self.identity_boundary,
                    self.permission_architecture, self.security_requirements,
                    self.monitoring_needs, self.failure_handling,
                    self.rollback_requirements, self.deferred_items,
                    self.implementation_order, self.decision)
        if any(not value for value in required):
            return Outcome.PREPARATION_REQUIRED
        if self.critical_blockers:
            return Outcome.PREPARATION_REQUIRED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
