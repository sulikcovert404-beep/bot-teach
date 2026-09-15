"""Phase-level governance package for transition planning; no runtime side effects."""
from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping

class TransitionGovernanceOutcome(str, Enum):
    TRANSITION_GOVERNANCE_READY="TRANSITION_GOVERNANCE_READY"
    TRANSITION_GOVERNANCE_READY_WITH_WARNINGS="TRANSITION_GOVERNANCE_READY_WITH_WARNINGS"
    TRANSITION_GOVERNANCE_INCOMPLETE="TRANSITION_GOVERNANCE_INCOMPLETE"
    TRANSITION_GOVERNANCE_BLOCKED="TRANSITION_GOVERNANCE_BLOCKED"
    UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class TransitionGovernancePackage:
    package_id: str
    ownership_model: Mapping[str,str]
    decision_authority_boundary: tuple[str,...]
    review_lifecycle: tuple[str,...]
    change_classification: Mapping[str,str]
    risk_acceptance_semantics: tuple[str,...]
    impact_review: tuple[str,...]
    sender_receiver_boundary: tuple[str,...]
    responsibility_transfer_rules: tuple[str,...]
    evidence_expectations: tuple[str,...]
    rollback_decision_semantics: tuple[str,...]
    failure_escalation: tuple[str,...]
    recovery_boundary: tuple[str,...]
    completeness_check: tuple[str,...]
    consistency_review: tuple[str,...]
    unresolved_risks: tuple[str,...]
    trace_reference: str
    package_digest: str
    transition_governance_only: bool = True
    execution: bool = False

    def outcome(self) -> TransitionGovernanceOutcome:
        if not self.package_id or not self.trace_reference or not self.package_digest:
            return TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_BLOCKED
        if not self.transition_governance_only or self.execution:
            return TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_INCOMPLETE
        groups=(self.ownership_model,self.decision_authority_boundary,self.review_lifecycle,self.change_classification,self.risk_acceptance_semantics,self.impact_review,self.sender_receiver_boundary,self.responsibility_transfer_rules,self.evidence_expectations,self.rollback_decision_semantics,self.failure_escalation,self.recovery_boundary,self.completeness_check,self.consistency_review)
        if any(not group for group in groups): return TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_INCOMPLETE
        return (TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_READY_WITH_WARNINGS if self.unresolved_risks else TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_READY)
