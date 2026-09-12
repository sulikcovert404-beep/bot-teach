"""Immutable preparation package for a controlled execution decision."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "EXECUTION_PACKAGE_READY"
    READY_WITH_WARNINGS = "EXECUTION_PACKAGE_READY_WITH_WARNINGS"
    DEFERRED = "EXECUTION_PACKAGE_DEFERRED"
    BLOCKED = "EXECUTION_PACKAGE_BLOCKED"


@dataclass(frozen=True)
class ControlledExecutionPreparationPackage:
    action_boundaries: Tuple[str, ...] = ()
    required_artifacts: Tuple[str, ...] = ()
    evidence_requirements: Tuple[str, ...] = ()
    decision_ownership: Tuple[str, ...] = ()
    approval_dependencies: Tuple[str, ...] = ()
    required_state: Tuple[str, ...] = ()
    prerequisites: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    rollback_readiness: Tuple[str, ...] = ()
    failure_handling: Tuple[str, ...] = ()
    recovery_verification: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    controlled_execution_preparation_only: bool = True
    execution_permission: bool = False
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.controlled_execution_preparation_only:
            return Outcome.BLOCKED
        if any((self.execution_permission, self.production_execution, self.deployment,
                self.migration_execution, self.database_change, self.credential_change,
                self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.action_boundaries, self.required_artifacts,
                    self.evidence_requirements, self.decision_ownership,
                    self.approval_dependencies, self.required_state,
                    self.prerequisites, self.rollback_readiness,
                    self.failure_handling, self.recovery_verification, self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        if self.blockers:
            return Outcome.BLOCKED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
