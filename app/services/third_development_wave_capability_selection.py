"""Immutable capability selection for the third development wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    SELECTED = "SELECTED_CAPABILITY"
    REJECTED = "REJECTED_CAPABILITIES"
    RATIONALE = "RATIONALE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ThirdDevelopmentWaveCapabilitySelection:
    available_capabilities: Tuple[str, ...] = ()
    business_technical_value: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    impact: Tuple[str, ...] = ()
    complexity: Tuple[str, ...] = ()
    risk: Tuple[str, ...] = ()
    architectural_fit: Tuple[str, ...] = ()
    existing_contracts: Tuple[str, ...] = ()
    rag_dependency: Tuple[str, ...] = ()
    implementation_isolation: Tuple[str, ...] = ()
    selected_capability: str = ""
    rejected_capabilities: Tuple[str, ...] = ()
    rationale: str = ""
    prerequisites: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    trace_reference: str = ""
    capability_selection_only: bool = True
    implementation_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.capability_selection_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required=(self.available_capabilities,self.business_technical_value,self.dependencies,self.impact,self.complexity,self.risk,self.architectural_fit,self.existing_contracts,self.rag_dependency,self.implementation_isolation,self.selected_capability,self.rationale,self.prerequisites)
        if any(not x for x in required) or self.selected_capability not in self.available_capabilities:
            return Outcome.BLOCKED
        return Outcome.SELECTED
