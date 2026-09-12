"""Immutable review for transitioning between capability waves."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    CLOSED = "CAPABILITY_WAVE_CLOSED"
    CLOSED_WITH_ACTIONS = "CAPABILITY_WAVE_CLOSED_WITH_ACTIONS"
    OPEN = "CAPABILITY_WAVE_OPEN"
    BLOCKED = "CAPABILITY_WAVE_BLOCKED"


@dataclass(frozen=True)
class CapabilityWaveTransitionReview:
    delivered_capability: str = ""
    achieved_objectives: Tuple[str, ...] = ()
    quality_status: Tuple[str, ...] = ()
    successful_patterns: Tuple[str, ...] = ()
    reusable_contracts: Tuple[str, ...] = ()
    discovered_constraints: Tuple[str, ...] = ()
    deferred_items: Tuple[str, ...] = ()
    future_decisions: Tuple[str, ...] = ()
    ownership: Tuple[str, ...] = ()
    readiness_conditions: Tuple[str, ...] = ()
    selection_rules: Tuple[str, ...] = ()
    dependency_check: Tuple[str, ...] = ()
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
