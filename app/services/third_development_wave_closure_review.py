"""Immutable closure record for the third development wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    CLOSED = "THIRD_WAVE_CLOSED"
    CLOSED_WITH_ACTIONS = "THIRD_WAVE_CLOSED_WITH_ACTIONS"
    OPEN = "THIRD_WAVE_OPEN"
    BLOCKED = "THIRD_WAVE_BLOCKED"


@dataclass(frozen=True)
class ThirdDevelopmentWaveClosureReview:
    implementation_outcome: str = ""
    validation_result: str = ""
    lessons_learned: Tuple[str, ...] = ()
    carryover_risks: Tuple[str, ...] = ()
    next_capability_entry_criteria: Tuple[str, ...] = ()
    trace_reference: str = ""
    closure_review_only: bool = True
    new_feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.closure_review_only:
            return Outcome.BLOCKED
        if any((self.new_feature_execution, self.runtime_execution, self.deployment,
                self.database_change, self.infrastructure_change, self.credential_change)):
            return Outcome.BLOCKED
        if self.implementation_outcome != "COMPLETE" or self.validation_result != "VALIDATED":
            return Outcome.OPEN
        required = (self.lessons_learned, self.next_capability_entry_criteria)
        if any(not value for value in required):
            return Outcome.OPEN
        return Outcome.CLOSED_WITH_ACTIONS if self.carryover_risks else Outcome.CLOSED
