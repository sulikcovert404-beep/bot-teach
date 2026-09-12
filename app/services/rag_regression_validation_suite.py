"""Immutable catalog of RAG regression scenarios and validation outcomes."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Tuple


class Outcome(StrEnum):
    STABLE = "RAG_VALIDATION_STABLE"
    STABLE_WITH_WARNINGS = "RAG_VALIDATION_STABLE_WITH_WARNINGS"
    INCOMPLETE = "RAG_VALIDATION_INCOMPLETE"
    BLOCKED = "RAG_VALIDATION_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RAGRegressionValidationSuite:
    baseline_scenarios: Tuple[str, ...] = ()
    expected_grounding_states: Tuple[str, ...] = ()
    failure_cases: Tuple[str, ...] = ()
    retrieval_request_validation: Tuple[str, ...] = ()
    source_guardian_behavior: Tuple[str, ...] = ()
    confidence_outcomes: Tuple[str, ...] = ()
    conflict_cases: Tuple[str, ...] = ()
    acceptance_criteria: Tuple[str, ...] = ()
    edge_cases: Tuple[str, ...] = ()
    compatibility_checks: Tuple[str, ...] = ()
    validated_behaviors: Tuple[str, ...] = ()
    known_limitations: Tuple[str, ...] = ()
    deferred_risks: Tuple[str, ...] = ()
    trace_reference: str = ""
    rag_validation_only: bool = True
    runtime_execution: bool = False
    deployment: bool = False
    provider_change: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.rag_validation_only or any((self.runtime_execution, self.deployment, self.provider_change, self.database_change, self.infrastructure_change)):
            return Outcome.INCOMPLETE
        required=(self.baseline_scenarios,self.expected_grounding_states,self.failure_cases,self.retrieval_request_validation,self.source_guardian_behavior,self.confidence_outcomes,self.acceptance_criteria,self.edge_cases,self.compatibility_checks,self.validated_behaviors)
        if any(not x for x in required):
            return Outcome.INCOMPLETE
        return Outcome.STABLE_WITH_WARNINGS if (self.deferred_risks or self.known_limitations) else Outcome.STABLE
