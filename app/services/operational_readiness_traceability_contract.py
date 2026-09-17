"""Trace design contract; storage, monitoring and execution tracking are prohibited."""
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class TraceOutcome(str, Enum):
    TRACE_CONTRACT_DEFINED="TRACE_CONTRACT_DEFINED"; TRACE_CONTRACT_DEFINED_WITH_WARNINGS="TRACE_CONTRACT_DEFINED_WITH_WARNINGS"; TRACE_CONTRACT_INCOMPLETE="TRACE_CONTRACT_INCOMPLETE"; TRACE_CONTRACT_BLOCKED="TRACE_CONTRACT_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessTraceabilityContract:
    trace_contract_id: str
    governance_model_reference: str
    assessment_framework_reference: str
    evidence_model_reference: str
    reference_graph: Mapping[str, str]
    lineage_rules: tuple[str, ...]
    trace_validation_rules: tuple[str, ...]
    integrity_constraints: tuple[str, ...]
    scope_exclusions: tuple[str, ...]
    boundary_assertions: Mapping[str, object]
    trace_digest: str

    def outcome(self) -> TraceOutcome:
        if not self.trace_contract_id or not self.governance_model_reference or not self.assessment_framework_reference or not self.evidence_model_reference or not self.trace_digest:
            return TraceOutcome.TRACE_CONTRACT_BLOCKED
        if not self.reference_graph or not self.lineage_rules or not self.trace_validation_rules:
            return TraceOutcome.TRACE_CONTRACT_INCOMPLETE
        if self.boundary_assertions.get("trace_storage") is not False or self.boundary_assertions.get("execution") is not False:
            return TraceOutcome.TRACE_CONTRACT_INCOMPLETE
        return TraceOutcome.TRACE_CONTRACT_DEFINED
