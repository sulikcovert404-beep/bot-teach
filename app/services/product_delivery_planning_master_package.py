"""Immutable, advisory product delivery plan."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "DELIVERY_PLAN_READY"
    READY_WITH_WARNINGS = "DELIVERY_PLAN_READY_WITH_WARNINGS"
    INCOMPLETE = "DELIVERY_PLAN_INCOMPLETE"
    BLOCKED = "DELIVERY_PLAN_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProductDeliveryPlanningMasterPackage:
    capability_priorities: Tuple[str, ...] = ()
    delivery_sequence: Tuple[str, ...] = ()
    milestone_grouping: Tuple[str, ...] = ()
    workstreams: Tuple[str, ...] = ()
    dependency_ordering: Tuple[str, ...] = ()
    technical_ownership: Tuple[str, ...] = ()
    release_boundaries: Tuple[str, ...] = ()
    acceptance_gates: Tuple[str, ...] = ()
    quality_checkpoints: Tuple[str, ...] = ()
    complexity_classification: Tuple[str, ...] = ()
    delivery_risks: Tuple[str, ...] = ()
    mitigation_planning: Tuple[str, ...] = ()
    recommended_next_phase: str = ""
    unresolved_decisions: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    trace_reference: str = ""
    delivery_planning_only: bool = True
    implementation_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.delivery_planning_only or any((self.implementation_execution,
                self.runtime_execution, self.deployment, self.database_change,
                self.infrastructure_change, self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.capability_priorities, self.delivery_sequence,
                    self.milestone_grouping, self.workstreams,
                    self.dependency_ordering, self.release_boundaries,
                    self.acceptance_gates, self.quality_checkpoints,
                    self.recommended_next_phase)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
