"""Immutable decision model for RAG confidence and source conflicts."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "RAG_DECISION_MODEL_READY"
    READY_WITH_WARNINGS = "RAG_DECISION_MODEL_READY_WITH_WARNINGS"
    INCOMPLETE = "RAG_DECISION_MODEL_INCOMPLETE"
    BLOCKED = "RAG_DECISION_MODEL_BLOCKED"


@dataclass(frozen=True)
class RAGConfidenceConflictDecisionWave:
    conflict_detection_semantics: Tuple[str, ...] = ()
    source_precedence_rules: Tuple[str, ...] = ()
    resolution_outcomes: Tuple[str, ...] = ()
    confidence_bands: Tuple[str, ...] = ()
    threshold_policy: Tuple[str, ...] = ()
    scoring_interpretation: Tuple[str, ...] = ()
    valid_source: Tuple[str, ...] = ()
    low_confidence: Tuple[str, ...] = ()
    conflicting_sources: Tuple[str, ...] = ()
    no_source: Tuple[str, ...] = ()
    backward_compatibility: Tuple[str, ...] = ()
    required_changes: Tuple[str, ...] = ()
    migration_risk: Tuple[str, ...] = ()
    approved_semantics: Tuple[str, ...] = ()
    deferred_items: Tuple[str, ...] = ()
    future_implementation_boundary: Tuple[str, ...] = ()
    trace_reference: str = ""
    rag_decision_design_only: bool = True
    runtime_execution: bool = False
    provider_change: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.rag_decision_design_only or any((self.runtime_execution, self.provider_change, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.INCOMPLETE
        required=(self.conflict_detection_semantics,self.source_precedence_rules,self.resolution_outcomes,self.confidence_bands,self.threshold_policy,self.scoring_interpretation,self.valid_source,self.low_confidence,self.conflicting_sources,self.no_source,self.backward_compatibility,self.required_changes,self.approved_semantics,self.future_implementation_boundary)
        if any(not x for x in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.deferred_items or self.migration_risk else Outcome.READY
