"""Immutable governance contract for future implementation work."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "IMPLEMENTATION_GOVERNANCE_READY"
    READY_WITH_WARNINGS = "IMPLEMENTATION_GOVERNANCE_READY_WITH_WARNINGS"
    INCOMPLETE = "IMPLEMENTATION_GOVERNANCE_INCOMPLETE"
    BLOCKED = "IMPLEMENTATION_GOVERNANCE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ImplementationGovernancePackage:
    coding_boundaries: Tuple[str, ...] = ()
    review_ownership: Tuple[str, ...] = ()
    change_ownership: Tuple[str, ...] = ()
    validation_requirements: Tuple[str, ...] = ()
    test_expectations: Tuple[str, ...] = ()
    review_checkpoints: Tuple[str, ...] = ()
    change_proposal: Tuple[str, ...] = ()
    implementation_review: Tuple[str, ...] = ()
    completion_criteria: Tuple[str, ...] = ()
    defect_classification: Tuple[str, ...] = ()
    escalation_path: Tuple[str, ...] = ()
    mitigation_model: Tuple[str, ...] = ()
    developer_handoff: Tuple[str, ...] = ()
    reviewer_handoff: Tuple[str, ...] = ()
    acceptance_boundary: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    trace_reference: str = ""
    implementation_governance_only: bool = True
    feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.implementation_governance_only or any((self.feature_execution,
                self.runtime_execution, self.deployment, self.database_change,
                self.infrastructure_change, self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.coding_boundaries, self.review_ownership,
                    self.change_ownership, self.validation_requirements,
                    self.test_expectations, self.change_proposal,
                    self.completion_criteria, self.defect_classification,
                    self.developer_handoff, self.acceptance_boundary)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
