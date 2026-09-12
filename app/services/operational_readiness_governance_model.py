"""Governance design model for readiness decisions; never grants execution authority."""
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class GovernanceOutcome(str, Enum):
    GOVERNANCE_DEFINED="GOVERNANCE_DEFINED"; GOVERNANCE_DEFINED_WITH_WARNINGS="GOVERNANCE_DEFINED_WITH_WARNINGS"; GOVERNANCE_INCOMPLETE="GOVERNANCE_INCOMPLETE"; GOVERNANCE_BLOCKED="GOVERNANCE_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessGovernanceModel:
    governance_id: str
    assessment_framework_reference: str
    governance_roles: Mapping[str, str]
    decision_boundaries: tuple[str, ...]
    review_requirements: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    escalation_rules: tuple[str, ...]
    scope_exclusions: tuple[str, ...]
    boundary_assertions: Mapping[str, object]
    trace_reference: str
    governance_digest: str

    def outcome(self) -> GovernanceOutcome:
        if not self.governance_id or not self.assessment_framework_reference or not self.trace_reference or not self.governance_digest:
            return GovernanceOutcome.GOVERNANCE_BLOCKED
        if not self.governance_roles or not self.decision_boundaries or not self.evidence_requirements:
            return GovernanceOutcome.GOVERNANCE_INCOMPLETE
        if self.boundary_assertions.get("execution") is not False or self.boundary_assertions.get("runtime_activation") != "PROHIBITED":
            return GovernanceOutcome.GOVERNANCE_INCOMPLETE
        return GovernanceOutcome.GOVERNANCE_DEFINED_WITH_WARNINGS if not self.review_requirements or not self.escalation_rules else GovernanceOutcome.GOVERNANCE_DEFINED
