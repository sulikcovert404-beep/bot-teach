"""Pure authorization readiness review for the third development wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "THIRD_WAVE_READY"
    READY_WITH_WARNINGS = "THIRD_WAVE_READY_WITH_WARNINGS"
    BLOCKED = "THIRD_WAVE_BLOCKED"


@dataclass(frozen=True)
class ThirdDevelopmentWaveAuthorizationReview:
    capability: str = ""
    objective: str = ""
    boundaries: Tuple[str, ...] = ()
    exclusions: Tuple[str, ...] = ()
    existing_modules: Tuple[str, ...] = ()
    contracts: Tuple[str, ...] = ()
    external_dependencies: Tuple[str, ...] = ()
    expected_files: Tuple[str, ...] = ()
    complexity: str = ""
    risk: str = ""
    acceptance_criteria: Tuple[str, ...] = ()
    test_strategy: Tuple[str, ...] = ()
    validation_requirements: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    trace_reference: str = ""
    authorization_review_only: bool = True
    implementation_permission: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.authorization_review_only:
            return Outcome.BLOCKED
        if any((self.implementation_permission, self.runtime_execution, self.deployment,
                self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required = (self.capability, self.objective, self.boundaries, self.exclusions,
                    self.existing_modules, self.contracts, self.expected_files,
                    self.acceptance_criteria, self.test_strategy,
                    self.validation_requirements)
        if any(not value for value in required):
            return Outcome.BLOCKED
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
