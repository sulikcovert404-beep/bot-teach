"""Immutable selection record for the first development capability."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    SELECTED = "WAVE_SCOPE_SELECTED"
    SELECTED_WITH_WARNINGS = "WAVE_SCOPE_SELECTED_WITH_WARNINGS"
    INCOMPLETE = "WAVE_SCOPE_INCOMPLETE"
    BLOCKED = "WAVE_SCOPE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FirstDevelopmentWaveScopeSelection:
    candidate_capabilities: tuple[str, ...] = ()
    selected_capability: str = ""
    priority_scoring: tuple[str, ...] = ()
    dependency_check: tuple[str, ...] = ()
    implementation_boundary: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    trace_reference: str = ""
    scope_selection_only: bool = True
    implementation_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.scope_selection_only or any((self.implementation_execution,
                self.runtime_execution, self.deployment, self.database_change,
                self.infrastructure_change, self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.candidate_capabilities, self.selected_capability,
                    self.priority_scoring, self.dependency_check,
                    self.implementation_boundary, self.acceptance_criteria)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        if self.selected_capability not in self.candidate_capabilities:
            return Outcome.INCOMPLETE
        return Outcome.SELECTED_WITH_WARNINGS if self.blockers else Outcome.SELECTED
