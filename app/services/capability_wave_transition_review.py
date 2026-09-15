"""Immutable review for transitioning between capability waves."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CLOSED = "CAPABILITY_WAVE_CLOSED"
    CLOSED_WITH_ACTIONS = "CAPABILITY_WAVE_CLOSED_WITH_ACTIONS"
    OPEN = "CAPABILITY_WAVE_OPEN"
    BLOCKED = "CAPABILITY_WAVE_BLOCKED"


@dataclass(frozen=True)
class CapabilityWaveTransitionReview:
    delivered_capability: str = ""
    achieved_objectives: tuple[str, ...] = ()
    quality_status: tuple[str, ...] = ()
    successful_patterns: tuple[str, ...] = ()
    reusable_contracts: tuple[str, ...] = ()
    discovered_constraints: tuple[str, ...] = ()
    deferred_items: tuple[str, ...] = ()
    future_decisions: tuple[str, ...] = ()
    ownership: tuple[str, ...] = ()
    readiness_conditions: tuple[str, ...] = ()
    selection_rules: tuple[str, ...] = ()
    dependency_check: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    capability_transition_review_only: bool = True
    new_capability_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.capability_transition_review_only or any((self.new_capability_execution, self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.OPEN
        required=(self.delivered_capability,self.achieved_objectives,self.quality_status,self.successful_patterns,self.reusable_contracts,self.readiness_conditions,self.selection_rules,self.dependency_check,self.decision)
        if any(not x for x in required):
            return Outcome.OPEN
        return Outcome.CLOSED_WITH_ACTIONS if (self.deferred_items or self.future_decisions) else Outcome.CLOSED
