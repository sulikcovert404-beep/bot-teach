"""Immutable preparation contract for a delivery wave."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "DELIVERY_WAVE_READY"
    READY_WITH_WARNINGS = "DELIVERY_WAVE_READY_WITH_WARNINGS"
    INCOMPLETE = "DELIVERY_WAVE_INCOMPLETE"
    BLOCKED = "DELIVERY_WAVE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DeliveryWavePreparationPackage:
    wave_scope: tuple[str, ...] = ()
    selected_capabilities: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    technical_prerequisites: tuple[str, ...] = ()
    dependency_readiness: tuple[str, ...] = ()
    development_constraints: tuple[str, ...] = ()
    test_requirements: tuple[str, ...] = ()
    review_checkpoints: tuple[str, ...] = ()
    acceptance_preparation: tuple[str, ...] = ()
    planned_change_boundaries: tuple[str, ...] = ()
    impact_classification: tuple[str, ...] = ()
    rollback_expectations: tuple[str, ...] = ()
    wave_rationale: str = ""
    expected_outcomes: tuple[str, ...] = ()
    remaining_blockers: tuple[str, ...] = ()
    trace_reference: str = ""
    delivery_wave_planning_only: bool = True
    implementation_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.delivery_wave_planning_only or any((self.implementation_execution,
                self.runtime_execution, self.deployment, self.database_change,
                self.infrastructure_change, self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.wave_scope, self.selected_capabilities, self.exclusions,
                    self.success_criteria, self.technical_prerequisites,
                    self.dependency_readiness, self.test_requirements,
                    self.acceptance_preparation, self.planned_change_boundaries,
                    self.rollback_expectations, self.wave_rationale)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.remaining_blockers else Outcome.READY
