"""Review design for readiness decisions; it cannot approve or execute anything."""
from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping

class ReviewOutcome(str, Enum):
    REVIEW_FRAMEWORK_DEFINED="REVIEW_FRAMEWORK_DEFINED"; REVIEW_FRAMEWORK_DEFINED_WITH_WARNINGS="REVIEW_FRAMEWORK_DEFINED_WITH_WARNINGS"; REVIEW_FRAMEWORK_INCOMPLETE="REVIEW_FRAMEWORK_INCOMPLETE"; REVIEW_FRAMEWORK_BLOCKED="REVIEW_FRAMEWORK_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessDecisionReviewFramework:
    review_framework_id: str; decision_framework_reference: str; review_roles: Mapping[str,str]; review_criteria: tuple[str,...]; review_checks: tuple[str,...]; challenge_rules: tuple[str,...]; escalation_rules: tuple[str,...]; review_constraints: tuple[str,...]; scope_exclusions: tuple[str,...]; boundary_assertions: Mapping[str,object]; trace_reference: str; review_digest: str
    def outcome(self)->ReviewOutcome:
        if not self.review_framework_id or not self.decision_framework_reference or not self.trace_reference or not self.review_digest: return ReviewOutcome.REVIEW_FRAMEWORK_BLOCKED
        if not self.review_roles or not self.review_criteria or not self.escalation_rules: return ReviewOutcome.REVIEW_FRAMEWORK_INCOMPLETE
        if self.boundary_assertions.get('approval_authority') is not False or self.boundary_assertions.get('execution') is not False: return ReviewOutcome.REVIEW_FRAMEWORK_INCOMPLETE
        return ReviewOutcome.REVIEW_FRAMEWORK_DEFINED
