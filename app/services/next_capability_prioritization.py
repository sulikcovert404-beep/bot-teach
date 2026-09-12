"""Immutable prioritization record for the next development capability."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    SELECTED = "CAPABILITY_SELECTED"
    SELECTED_WITH_WARNINGS = "CAPABILITY_SELECTED_WITH_WARNINGS"
    INCOMPLETE = "CAPABILITY_SELECTION_INCOMPLETE"
    BLOCKED = "CAPABILITY_SELECTION_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NextCapabilityPrioritization:
    available_capabilities: Tuple[str, ...] = ()
    business_technical_value: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    impact: Tuple[str, ...] = ()
    complexity: Tuple[str, ...] = ()
    risk: Tuple[str, ...] = ()
    dependency_weight: Tuple[str, ...] = ()
    rag_dependency: Tuple[str, ...] = ()
    architecture_fit: Tuple[str, ...] = ()
    existing_contracts: Tuple[str, ...] = ()
    selected_capability: str = ""
    rejected_candidates: Tuple[str, ...] = ()
    rationale: str = ""
    approved_next_wave: str = ""
    blockers: Tuple[str, ...] = ()
    prerequisites: Tuple[str, ...] = ()
    trace_reference: str = ""
    capability_selection_only: bool = True
    new_capability_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.capability_selection_only or any((self.new_capability_execution, self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.INCOMPLETE
        required=(self.available_capabilities,self.business_technical_value,self.dependencies,self.impact,self.complexity,self.risk,self.dependency_weight,self.rag_dependency,self.architecture_fit,self.existing_contracts,self.selected_capability,self.rationale,self.approved_next_wave,self.prerequisites)
        if any(not x for x in required) or self.selected_capability not in self.available_capabilities:
            return Outcome.INCOMPLETE
        return Outcome.SELECTED_WITH_WARNINGS if self.blockers else Outcome.SELECTED
