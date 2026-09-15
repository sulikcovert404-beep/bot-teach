"""Immutable governance contract for future implementation work."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "IMPLEMENTATION_GOVERNANCE_READY"
    READY_WITH_WARNINGS = "IMPLEMENTATION_GOVERNANCE_READY_WITH_WARNINGS"
    INCOMPLETE = "IMPLEMENTATION_GOVERNANCE_INCOMPLETE"
    BLOCKED = "IMPLEMENTATION_GOVERNANCE_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ImplementationGovernancePackage:
    coding_boundaries: tuple[str, ...] = ()
    review_ownership: tuple[str, ...] = ()
    change_ownership: tuple[str, ...] = ()
    validation_requirements: tuple[str, ...] = ()
    test_expectations: tuple[str, ...] = ()
    review_checkpoints: tuple[str, ...] = ()
    change_proposal: tuple[str, ...] = ()
    implementation_review: tuple[str, ...] = ()
    completion_criteria: tuple[str, ...] = ()
    defect_classification: tuple[str, ...] = ()
    escalation_path: tuple[str, ...] = ()
    mitigation_model: tuple[str, ...] = ()
    developer_handoff: tuple[str, ...] = ()
    reviewer_handoff: tuple[str, ...] = ()
    acceptance_boundary: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
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
