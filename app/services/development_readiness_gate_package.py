"""Immutable gate describing readiness to begin development; no permission is granted."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "DEVELOPMENT_READY"
    READY_WITH_WARNINGS = "DEVELOPMENT_READY_WITH_WARNINGS"
    NOT_READY = "DEVELOPMENT_NOT_READY"
    BLOCKED = "DEVELOPMENT_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DevelopmentReadinessGatePackage:
    tooling_assumptions: Tuple[str, ...] = ()
    workspace_requirements: Tuple[str, ...] = ()
    dependency_readiness: Tuple[str, ...] = ()
    coding_workflow: Tuple[str, ...] = ()
    review_process: Tuple[str, ...] = ()
    validation_process: Tuple[str, ...] = ()
    test_readiness: Tuple[str, ...] = ()
    acceptance_readiness: Tuple[str, ...] = ()
    defect_handling_model: Tuple[str, ...] = ()
    ownership: Tuple[str, ...] = ()
    responsibility: Tuple[str, ...] = ()
    escalation: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    prerequisites: Tuple[str, ...] = ()
    trace_reference: str = ""
    development_readiness_only: bool = True
    feature_implementation: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_setup: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.development_readiness_only or any((self.feature_implementation,
                self.runtime_execution, self.deployment, self.database_change,
                self.infrastructure_setup, self.credential_change)):
            return Outcome.NOT_READY
        required = (self.tooling_assumptions, self.workspace_requirements,
                    self.dependency_readiness, self.coding_workflow,
                    self.review_process, self.validation_process,
                    self.test_readiness, self.acceptance_readiness,
                    self.ownership, self.responsibility, self.prerequisites)
        if any(not item for item in required):
            return Outcome.NOT_READY
        return Outcome.READY_WITH_WARNINGS if self.blockers else Outcome.READY
