"""Immutable, non-authoritative inventory of the platform architecture."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    CONSOLIDATED = "ARCHITECTURE_CONSOLIDATED"
    CONSOLIDATED_WITH_WARNINGS = "ARCHITECTURE_CONSOLIDATED_WITH_WARNINGS"
    INCOMPLETE = "ARCHITECTURE_INCOMPLETE"
    BLOCKED = "ARCHITECTURE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MasterArchitectureConsolidationPackage:
    architecture_map: Tuple[str, ...] = ()
    implemented_contracts: Tuple[str, ...] = ()
    design_artifacts: Tuple[str, ...] = ()
    prohibited_areas: Tuple[str, ...] = ()
    dependency_graph: Tuple[str, ...] = ()
    lineage_summary: Tuple[str, ...] = ()
    open_risks: Tuple[str, ...] = ()
    forbidden_transitions: Tuple[str, ...] = ()
    unresolved_items: Tuple[str, ...] = ()
    future_entry_conditions: Tuple[str, ...] = ()
    prerequisites: Tuple[str, ...] = ()
    restrictions: Tuple[str, ...] = ()
    trace_reference: str = ""
    architecture_consolidation_only: bool = True
    runtime_execution: bool = False
    runtime_control: bool = False
    command_execution: bool = False
    runtime_activation: bool = False
    runtime_admission: bool = False
    deployment: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.architecture_consolidation_only:
            return Outcome.INCOMPLETE
        if any((self.runtime_execution, self.runtime_control, self.command_execution,
                self.runtime_activation, self.runtime_admission, self.deployment,
                self.infrastructure_change)):
            return Outcome.INCOMPLETE
        required = (self.architecture_map, self.implemented_contracts,
                    self.design_artifacts, self.prohibited_areas,
                    self.dependency_graph, self.lineage_summary,
                    self.future_entry_conditions)
        return Outcome.CONSOLIDATED if all(required) else Outcome.INCOMPLETE
