"""Immutable kickoff record for the first implementation wave."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "KICKOFF_READY"
    READY_WITH_WARNINGS = "KICKOFF_READY_WITH_WARNINGS"
    INCOMPLETE = "KICKOFF_INCOMPLETE"
    BLOCKED = "KICKOFF_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ImplementationKickoffPackage:
    wave_objective: str = ""
    scope_boundary: tuple[str, ...] = ()
    expected_deliverables: tuple[str, ...] = ()
    work_items: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    ownership: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    required_reviews: tuple[str, ...] = ()
    validation_checkpoints: tuple[str, ...] = ()
    done_criteria: tuple[str, ...] = ()
    quality_gates: tuple[str, ...] = ()
    handoff_conditions: tuple[str, ...] = ()
    decision: str = ""
    blockers: tuple[str, ...] = ()
    next_action: str = ""
    trace_reference: str = ""
    implementation_kickoff_only: bool = True
    feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.implementation_kickoff_only or any((self.feature_execution,
                self.runtime_execution, self.deployment, self.database_change,
                self.infrastructure_change, self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.wave_objective, self.scope_boundary, self.expected_deliverables,
                    self.work_items, self.dependencies, self.ownership,
                    self.prerequisites, self.required_reviews,
                    self.validation_checkpoints, self.done_criteria,
                    self.quality_gates, self.handoff_conditions, self.decision,
                    self.next_action)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.blockers else Outcome.READY
