"""Immutable authorization review for the second development wave."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "SECOND_WAVE_READY"
    READY_WITH_WARNINGS = "SECOND_WAVE_READY_WITH_WARNINGS"
    BLOCKED = "SECOND_WAVE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SecondDevelopmentWaveAuthorizationReview:
    capability_confirmation: str = ""
    scope_boundary: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    existing_contracts: tuple[str, ...] = ()
    required_prerequisites: tuple[str, ...] = ()
    dependency_risks: tuple[str, ...] = ()
    expected_modules: tuple[str, ...] = ()
    affected_areas: tuple[str, ...] = ()
    complexity_assessment: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    test_strategy: tuple[str, ...] = ()
    validation_requirements: tuple[str, ...] = ()
    decision: str = ""
    blockers: tuple[str, ...] = ()
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
