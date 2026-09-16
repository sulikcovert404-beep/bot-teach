from app.services.transition_governance_package import (
 TransitionGovernanceOutcome,
 TransitionGovernancePackage,
)


def make(**o):
 d=dict(package_id="g-1",ownership_model={"sender":"admin"},decision_authority_boundary=("commander",),review_lifecycle=("review",),change_classification={"schema":"high"},risk_acceptance_semantics=("explicit",),impact_review=("required",),sender_receiver_boundary=("admin->executor",),responsibility_transfer_rules=("ack",),evidence_expectations=("trace",),rollback_decision_semantics=("commander",),failure_escalation=("operator",),recovery_boundary=("governance",),completeness_check=("all",),consistency_review=("cross-check",),unresolved_risks=(),trace_reference="t",package_digest="d")
 d.update(o); return TransitionGovernancePackage(**d)
def test_ready(): assert make().outcome() is TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_READY
def test_warning_blocked():
 assert make(unresolved_risks=("open",)).outcome() is TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_READY_WITH_WARNINGS
 assert make(package_digest="").outcome() is TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_BLOCKED
def test_incomplete(): assert make(impact_review=()).outcome() is TransitionGovernanceOutcome.TRANSITION_GOVERNANCE_INCOMPLETE
