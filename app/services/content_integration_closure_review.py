"""Immutable closure record for the content integration phase."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CLOSED = "CONTENT_INTEGRATION_CLOSED"
    CLOSED_WITH_ACTIONS = "CONTENT_INTEGRATION_CLOSED_WITH_ACTIONS"
    OPEN = "CONTENT_INTEGRATION_OPEN"
    BLOCKED = "CONTENT_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class ContentIntegrationClosureReview:
    implementation_outcome: str = ""
    validation_result: str = ""
    warning_register: tuple[str, ...] = ()
    lessons_learned: tuple[str, ...] = ()
    future_entry_criteria: tuple[str, ...] = ()
    trace_reference: str = ""
    closure_review_only: bool = True
    new_feature_execution: bool = False
    database_change: bool = False
    migration_execution: bool = False
    deployment: bool = False
    runtime_execution: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.closure_review_only:
            return Outcome.BLOCKED
        if any((self.new_feature_execution, self.database_change,
                self.migration_execution, self.deployment, self.runtime_execution,
                self.credential_change)):
            return Outcome.BLOCKED
        if self.implementation_outcome != "COMPLETE" or self.validation_result not in {"VALIDATED", "VALIDATED_WITH_WARNINGS"}:
            return Outcome.OPEN
        if not self.lessons_learned or not self.future_entry_criteria:
            return Outcome.OPEN
        return Outcome.CLOSED_WITH_ACTIONS if self.warning_register else Outcome.CLOSED
