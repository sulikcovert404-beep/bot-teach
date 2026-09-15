"""Immutable closure review for the second development wave."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CLOSED = "SECOND_WAVE_CLOSED"
    CLOSED_WITH_ACTIONS = "SECOND_WAVE_CLOSED_WITH_ACTIONS"
    OPEN = "SECOND_WAVE_OPEN"
    BLOCKED = "SECOND_WAVE_BLOCKED"


@dataclass(frozen=True)
class SecondDevelopmentWaveClosureReview:
    delivered_changes: tuple[str, ...] = ()
    objective_achievement: tuple[str, ...] = ()
    scope_compliance: tuple[str, ...] = ()
    test_validation: tuple[str, ...] = ()
    regression_status: tuple[str, ...] = ()
    compatibility_review: tuple[str, ...] = ()
    carryover_risks: tuple[str, ...] = ()
    reusable_patterns: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    improvements: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    second_wave_closure_review_only: bool = True
    new_feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.second_wave_closure_review_only or any((self.new_feature_execution, self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.OPEN
        required=(self.delivered_changes,self.objective_achievement,self.scope_compliance,self.test_validation,self.regression_status,self.compatibility_review,self.reusable_patterns,self.decision)
        if any(not x for x in required):
            return Outcome.OPEN
        return Outcome.CLOSED_WITH_ACTIONS if self.carryover_risks or self.constraints or self.improvements else Outcome.CLOSED
