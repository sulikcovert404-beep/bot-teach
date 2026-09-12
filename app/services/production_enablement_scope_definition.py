"""Immutable scope definition for production enablement."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    DEFINED = "PRODUCTION_ENABLEMENT_SCOPE_DEFINED"
    DEFINED_WITH_WARNINGS = "PRODUCTION_ENABLEMENT_SCOPE_DEFINED_WITH_WARNINGS"
    INCOMPLETE = "PRODUCTION_ENABLEMENT_SCOPE_INCOMPLETE"
    BLOCKED = "PRODUCTION_ENABLEMENT_SCOPE_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementScopeDefinition:
    production_capability: Tuple[str, ...] = ()
    out_of_scope: Tuple[str, ...] = ()
    storage_target: Tuple[str, ...] = ()
    migration_boundary: Tuple[str, ...] = ()
    rollback_requirements: Tuple[str, ...] = ()
    identity_integration: Tuple[str, ...] = ()
    permission_rollout: Tuple[str, ...] = ()
    activation_boundary: Tuple[str, ...] = ()
    operational_ownership: Tuple[str, ...] = ()
    success_criteria: Tuple[str, ...] = ()
    safety_gates: Tuple[str, ...] = ()
    stop_conditions: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    production_enablement_scope_only: bool = True
    execution_permission: bool = False
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.production_enablement_scope_only:
            return Outcome.BLOCKED
        if any((self.execution_permission, self.production_execution, self.deployment,
                self.migration_execution, self.database_change, self.credential_change,
                self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.production_capability, self.out_of_scope, self.storage_target,
                    self.migration_boundary, self.rollback_requirements,
                    self.identity_integration, self.permission_rollout,
                    self.activation_boundary, self.operational_ownership,
                    self.success_criteria, self.safety_gates, self.stop_conditions,
                    self.decision)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.DEFINED_WITH_WARNINGS if self.warnings else Outcome.DEFINED
