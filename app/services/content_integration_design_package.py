"""Provider-neutral design record for future content integration."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    DESIGNED = "CONTENT_INTEGRATION_DESIGNED"
    DESIGNED_WITH_WARNINGS = "CONTENT_INTEGRATION_DESIGNED_WITH_WARNINGS"
    INCOMPLETE = "CONTENT_INTEGRATION_INCOMPLETE"
    BLOCKED = "CONTENT_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class ContentIntegrationDesignPackage:
    data_model_requirements: Tuple[str, ...] = ()
    storage_contract: Tuple[str, ...] = ()
    lifecycle_states: Tuple[str, ...] = ()
    consistency_rules: Tuple[str, ...] = ()
    migration_impact: Tuple[str, ...] = ()
    permission_model: Tuple[str, ...] = ()
    ownership_rules: Tuple[str, ...] = ()
    access_matrix: Tuple[str, ...] = ()
    security_boundaries: Tuple[str, ...] = ()
    component_interaction: Tuple[str, ...] = ()
    dependency_flow: Tuple[str, ...] = ()
    interface_contracts: Tuple[str, ...] = ()
    validation_strategy: Tuple[str, ...] = ()
    rollback_considerations: Tuple[str, ...] = ()
    failure_handling: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    integration_design_only: bool = True
    implementation_execution: bool = False
    database_change: bool = False
    migration_execution: bool = False
    authorization_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.integration_design_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.database_change,
                self.migration_execution, self.authorization_execution,
                self.runtime_execution, self.deployment, self.infrastructure_change)):
            return Outcome.BLOCKED
        required = (self.data_model_requirements, self.storage_contract,
                    self.lifecycle_states, self.consistency_rules, self.migration_impact,
                    self.permission_model, self.ownership_rules, self.access_matrix,
                    self.security_boundaries, self.component_interaction,
                    self.dependency_flow, self.interface_contracts,
                    self.validation_strategy, self.rollback_considerations,
                    self.failure_handling, self.decision)
        return (Outcome.INCOMPLETE if any(not item for item in required)
                else Outcome.DESIGNED_WITH_WARNINGS if self.warnings
                else Outcome.DESIGNED)
