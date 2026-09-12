"""Immutable production-readiness assessment; no production side effects."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "PRODUCTION_READY"
    READY_WITH_WARNINGS = "PRODUCTION_READY_WITH_WARNINGS"
    PREPARATION_REQUIRED = "PRODUCTION_PREPARATION_REQUIRED"
    BLOCKED = "PRODUCTION_BLOCKED"


@dataclass(frozen=True)
class ProductionReadinessAssessment:
    storage_options: Tuple[str, ...] = ()
    durability_requirements: Tuple[str, ...] = ()
    migration_readiness: Tuple[str, ...] = ()
    identity_boundary: Tuple[str, ...] = ()
    permission_architecture: Tuple[str, ...] = ()
    security_requirements: Tuple[str, ...] = ()
    monitoring_needs: Tuple[str, ...] = ()
    failure_handling: Tuple[str, ...] = ()
    rollback_requirements: Tuple[str, ...] = ()
    critical_blockers: Tuple[str, ...] = ()
    deferred_items: Tuple[str, ...] = ()
    implementation_order: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
