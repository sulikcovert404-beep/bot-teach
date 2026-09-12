"""Immutable design package for production enablement."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    DESIGNED = "PRODUCTION_ENABLEMENT_DESIGNED"
    DESIGNED_WITH_WARNINGS = "PRODUCTION_ENABLEMENT_DESIGNED_WITH_WARNINGS"
    INCOMPLETE = "PRODUCTION_ENABLEMENT_INCOMPLETE"
    BLOCKED = "PRODUCTION_ENABLEMENT_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementDesignPackage:
    storage_architecture: Tuple[str, ...] = ()
    migration_strategy: Tuple[str, ...] = ()
    data_validation: Tuple[str, ...] = ()
    rollback_design: Tuple[str, ...] = ()
    identity_integration: Tuple[str, ...] = ()
    permission_mapping: Tuple[str, ...] = ()
    security_controls: Tuple[str, ...] = ()
    activation_sequence: Tuple[str, ...] = ()
    operational_ownership: Tuple[str, ...] = ()
    monitoring_model: Tuple[str, ...] = ()
    release_strategy: Tuple[str, ...] = ()
    checkpoints: Tuple[str, ...] = ()
    recovery_flow: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
