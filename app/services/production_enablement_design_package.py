"""Immutable design package for production enablement."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    DESIGNED = "PRODUCTION_ENABLEMENT_DESIGNED"
    DESIGNED_WITH_WARNINGS = "PRODUCTION_ENABLEMENT_DESIGNED_WITH_WARNINGS"
    INCOMPLETE = "PRODUCTION_ENABLEMENT_INCOMPLETE"
    BLOCKED = "PRODUCTION_ENABLEMENT_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementDesignPackage:
    storage_architecture: tuple[str, ...] = ()
    migration_strategy: tuple[str, ...] = ()
    data_validation: tuple[str, ...] = ()
    rollback_design: tuple[str, ...] = ()
    identity_integration: tuple[str, ...] = ()
    permission_mapping: tuple[str, ...] = ()
    security_controls: tuple[str, ...] = ()
    activation_sequence: tuple[str, ...] = ()
    operational_ownership: tuple[str, ...] = ()
    monitoring_model: tuple[str, ...] = ()
    release_strategy: tuple[str, ...] = ()
    checkpoints: tuple[str, ...] = ()
    recovery_flow: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    production_enablement_design_only: bool = True
    implementation_execution: bool = False
    migration_execution: bool = False
    database_change: bool = False
    deployment: bool = False
    runtime_activation: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.production_enablement_design_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.migration_execution,
                self.database_change, self.deployment, self.runtime_activation,
                self.credential_change)):
            return Outcome.BLOCKED
        required = (self.storage_architecture, self.migration_strategy,
                    self.data_validation, self.rollback_design,
                    self.identity_integration, self.permission_mapping,
                    self.security_controls, self.activation_sequence,
                    self.operational_ownership, self.monitoring_model,
                    self.release_strategy, self.checkpoints, self.recovery_flow,
                    self.decision)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.DESIGNED_WITH_WARNINGS if self.warnings else Outcome.DESIGNED
