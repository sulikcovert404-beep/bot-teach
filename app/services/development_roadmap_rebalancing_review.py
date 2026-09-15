"""Immutable roadmap rebalancing review after completed capability waves."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CONTINUE = "CONTINUE_CURRENT_CAPABILITY"
    SELECT = "SELECT_NEW_CAPABILITY"
    REBALANCE = "REBALANCE_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class DevelopmentRoadmapRebalancingReview:
    completed_capabilities: tuple[str, ...] = ()
    delivered_value: tuple[str, ...] = ()
    remaining_risks: tuple[str, ...] = ()
    pending_capabilities: tuple[str, ...] = ()
    pending_dependencies: tuple[str, ...] = ()
    pending_priorities: tuple[str, ...] = ()
    continue_rag_runtime: tuple[str, ...] = ()
    start_new_capability: tuple[str, ...] = ()
    complexity: tuple[str, ...] = ()
    risk: tuple[str, ...] = ()
    expected_value: tuple[str, ...] = ()
    recommendation: str = ""
    trace_reference: str = ""
    roadmap_review_only: bool = True
    runtime_execution: bool = False
    deployment: bool = False
    provider_change: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.roadmap_review_only or any((self.runtime_execution, self.deployment, self.provider_change, self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required=(self.completed_capabilities,self.delivered_value,self.pending_capabilities,self.pending_dependencies,self.pending_priorities,self.complexity,self.risk,self.expected_value,self.recommendation)
        return Outcome.REBALANCE if any(not x for x in required) else Outcome(self.recommendation)
