"""Immutable impact review for propagating RAG decision semantics."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "RAG_INTEGRATION_READY"
    READY_WITH_WARNINGS = "RAG_INTEGRATION_READY_WITH_WARNINGS"
    BLOCKED = "RAG_INTEGRATION_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RAGIntegrationImpactReviewWave:
    consumers: Tuple[str, ...] = ()
    downstream_behavior: Tuple[str, ...] = ()
    compatibility_boundaries: Tuple[str, ...] = ()
    affected_interfaces: Tuple[str, ...] = ()
    required_updates: Tuple[str, ...] = ()
    backward_compatibility: Tuple[str, ...] = ()
    existing_tests: Tuple[str, ...] = ()
    missing_scenarios: Tuple[str, ...] = ()
    future_regression_needs: Tuple[str, ...] = ()
    breaking_risks: Tuple[str, ...] = ()
    migration_risks: Tuple[str, ...] = ()
    deferred_changes: Tuple[str, ...] = ()
    approved_decision: str = ""
    trace_reference: str = ""
    rag_integration_review_only: bool = True
    runtime_execution: bool = False
    provider_change: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.rag_integration_review_only or any((self.runtime_execution, self.provider_change, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required=(self.consumers,self.downstream_behavior,self.compatibility_boundaries,self.affected_interfaces,self.required_updates,self.backward_compatibility,self.existing_tests,self.missing_scenarios,self.future_regression_needs,self.approved_decision)
        if any(not x for x in required):
            return Outcome.BLOCKED
        return Outcome.READY_WITH_WARNINGS if (self.breaking_risks or self.migration_risks or self.deferred_changes) else Outcome.READY
