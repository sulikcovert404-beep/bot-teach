"""Immutable preparation record for production enablement implementation."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "IMPLEMENTATION_PACKAGE_READY"
    READY_WITH_WARNINGS = "IMPLEMENTATION_PACKAGE_READY_WITH_WARNINGS"
    BLOCKED = "IMPLEMENTATION_PACKAGE_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementImplementationPreparation:
    change_list: Tuple[str, ...] = ()
    module_boundaries: Tuple[str, ...] = ()
    dependency_order: Tuple[str, ...] = ()
    migration_steps_draft: Tuple[str, ...] = ()
    validation_checkpoints: Tuple[str, ...] = ()
    rollback_checkpoints: Tuple[str, ...] = ()
    identity_integration_tasks: Tuple[str, ...] = ()
    permission_mapping_tasks: Tuple[str, ...] = ()
    deployment_sequence: Tuple[str, ...] = ()
    verification_steps: Tuple[str, ...] = ()
    stop_conditions: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    production_enablement_preparation_only: bool = True
    implementation_execution: bool = False
    migration_execution: bool = False
    database_change: bool = False
    deployment: bool = False
    runtime_activation: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.production_enablement_preparation_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.migration_execution,
                self.database_change, self.deployment, self.runtime_activation,
                self.credential_change)):
            return Outcome.BLOCKED
        required = (self.change_list, self.module_boundaries, self.dependency_order,
                    self.migration_steps_draft, self.validation_checkpoints,
                    self.rollback_checkpoints, self.identity_integration_tasks,
                    self.permission_mapping_tasks, self.deployment_sequence,
                    self.verification_steps, self.stop_conditions, self.decision)
        if any(not item for item in required):
            return Outcome.BLOCKED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
