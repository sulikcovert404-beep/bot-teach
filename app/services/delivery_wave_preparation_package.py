"""Immutable preparation contract for a delivery wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "DELIVERY_WAVE_READY"
    READY_WITH_WARNINGS = "DELIVERY_WAVE_READY_WITH_WARNINGS"
    INCOMPLETE = "DELIVERY_WAVE_INCOMPLETE"
    BLOCKED = "DELIVERY_WAVE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DeliveryWavePreparationPackage:
    wave_scope: Tuple[str, ...] = ()
    selected_capabilities: Tuple[str, ...] = ()
    exclusions: Tuple[str, ...] = ()
    success_criteria: Tuple[str, ...] = ()
    technical_prerequisites: Tuple[str, ...] = ()
    dependency_readiness: Tuple[str, ...] = ()
    development_constraints: Tuple[str, ...] = ()
    test_requirements: Tuple[str, ...] = ()
    review_checkpoints: Tuple[str, ...] = ()
    acceptance_preparation: Tuple[str, ...] = ()
    planned_change_boundaries: Tuple[str, ...] = ()
    impact_classification: Tuple[str, ...] = ()
    rollback_expectations: Tuple[str, ...] = ()
    wave_rationale: str = ""
    expected_outcomes: Tuple[str, ...] = ()
    remaining_blockers: Tuple[str, ...] = ()
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
