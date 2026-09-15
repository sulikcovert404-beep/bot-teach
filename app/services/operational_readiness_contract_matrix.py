"""Immutable contract matrix; descriptive only and grants no operational authority."""
from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping

class MatrixOutcome(str, Enum):
    MATRIX_READY="MATRIX_READY"; MATRIX_READY_WITH_WARNINGS="MATRIX_READY_WITH_WARNINGS"; MATRIX_INCOMPLETE="MATRIX_INCOMPLETE"; MATRIX_BLOCKED="MATRIX_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessContractMatrix:
    matrix_id: str; operational_design_foundation_reference: str; capability_inventory: tuple[str,...]; dependency_matrix: Mapping[str, tuple[str,...]]; control_requirements: tuple[str,...]; risk_matrix: Mapping[str,str]; scope_exclusions: tuple[str,...]; transition_constraints: tuple[str,...]; boundary_assertions: Mapping[str,object]; trace_reference: str; matrix_digest: str
    def outcome(self)->MatrixOutcome:
        if not self.matrix_id or not self.operational_design_foundation_reference or not self.trace_reference or not self.matrix_digest: return MatrixOutcome.MATRIX_BLOCKED
        if not self.capability_inventory or any(not v for v in self.dependency_matrix.values()): return MatrixOutcome.MATRIX_INCOMPLETE
        if self.boundary_assertions.get("execution") is not False or self.boundary_assertions.get("runtime_activation") != "PROHIBITED": return MatrixOutcome.MATRIX_INCOMPLETE
        return MatrixOutcome.MATRIX_READY_WITH_WARNINGS if self.risk_matrix else MatrixOutcome.MATRIX_READY
