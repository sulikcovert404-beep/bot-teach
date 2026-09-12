"""Immutable authorization review for the second development wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "SECOND_WAVE_READY"
    READY_WITH_WARNINGS = "SECOND_WAVE_READY_WITH_WARNINGS"
    BLOCKED = "SECOND_WAVE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SecondDevelopmentWaveAuthorizationReview:
    capability_confirmation: str = ""
    scope_boundary: Tuple[str, ...] = ()
    exclusions: Tuple[str, ...] = ()
    existing_contracts: Tuple[str, ...] = ()
    required_prerequisites: Tuple[str, ...] = ()
    dependency_risks: Tuple[str, ...] = ()
    expected_modules: Tuple[str, ...] = ()
    affected_areas: Tuple[str, ...] = ()
    complexity_assessment: Tuple[str, ...] = ()
    acceptance_criteria: Tuple[str, ...] = ()
    test_strategy: Tuple[str, ...] = ()
    validation_requirements: Tuple[str, ...] = ()
    decision: str = ""
    blockers: Tuple[str, ...] = ()
    trace_reference: str = ""
    second_wave_authorization_review_only: bool = True
    implementation_permission: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.second_wave_authorization_review_only or self.implementation_permission or any((self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required=(self.capability_confirmation,self.scope_boundary,self.exclusions,self.existing_contracts,self.required_prerequisites,self.expected_modules,self.affected_areas,self.acceptance_criteria,self.test_strategy,self.validation_requirements,self.decision)
        if any(not x for x in required):
            return Outcome.BLOCKED
        return Outcome.READY_WITH_WARNINGS if self.blockers else Outcome.READY
