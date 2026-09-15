"""Immutable closure review for a completed development wave."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CLOSED = "WAVE_CLOSED"
    CLOSED_WITH_ACTIONS = "WAVE_CLOSED_WITH_ACTIONS"
    NOT_CLOSED = "WAVE_NOT_CLOSED"
    BLOCKED = "WAVE_BLOCKED"


@dataclass(frozen=True)
class DevelopmentWaveClosureReview:
    delivered_changes: tuple[str, ...] = ()
    achieved_objectives: tuple[str, ...] = ()
    deviation_analysis: tuple[str, ...] = ()
    test_coverage: tuple[str, ...] = ()
    validation_results: tuple[str, ...] = ()
    regression_assessment: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    future_decisions: tuple[str, ...] = ()
    technical_debt: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    wave_closure_review_only: bool = True
    new_feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.wave_closure_review_only or any((self.new_feature_execution, self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.NOT_CLOSED
        required=(self.delivered_changes,self.achieved_objectives,self.test_coverage,self.validation_results,self.regression_assessment,self.decision)
        if any(not x for x in required):
            return Outcome.NOT_CLOSED
        return Outcome.CLOSED_WITH_ACTIONS if (self.unresolved_items or self.future_decisions or self.technical_debt) else Outcome.CLOSED
