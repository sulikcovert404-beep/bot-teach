"""Immutable closure record for the architecture program."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CLOSED = "PROGRAM_CLOSED"
    CLOSED_WITH_WARNINGS = "PROGRAM_CLOSED_WITH_WARNINGS"
    OPEN = "PROGRAM_OPEN"
    BLOCKED = "PROGRAM_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ArchitectureProgramClosurePackage:
    final_architecture_summary: tuple[str, ...] = ()
    artifact_inventory: tuple[str, ...] = ()
    dependency_closure: tuple[str, ...] = ()
    risk_closure: tuple[str, ...] = ()
    final_boundary_register: tuple[str, ...] = ()
    future_phase_entry_criteria: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    trace_reference: str = ""
    program_closure_only: bool = True
    runtime_execution: bool = False
    runtime_control: bool = False
    execution: bool = False
    deployment: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.program_closure_only or any((self.runtime_execution, self.runtime_control,
                self.execution, self.deployment, self.infrastructure_change)):
            return Outcome.OPEN
        required = (self.final_architecture_summary, self.artifact_inventory,
                    self.dependency_closure, self.risk_closure,
                    self.final_boundary_register, self.future_phase_entry_criteria)
        if any(not item for item in required):
            return Outcome.OPEN
        return Outcome.CLOSED_WITH_WARNINGS if self.warnings else Outcome.CLOSED
