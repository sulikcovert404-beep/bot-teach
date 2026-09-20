from app.services.pre_execution_master_review_package import *


def make(**o):
 d={"review_id": "r","governance_closure_reference": "g","governance_meta_validation_reference": "m","boundary_verification": ("ok",),"finalization_reference": "f","state_consistency_reference": "s","assurance_reference": "a","transition_governance_reference": "tg","transition_certification_reference": "tc","open_risks": (),"unresolved_dependencies": (),"escalation_status": ("none",),"overall_posture": "ready","constraints": ("design-only",),"blocked_items": (),"trace_reference": "t","review_digest": "d"}; d.update(o); return PreExecutionMasterReviewPackage(**d)
def test_ready(): assert make().outcome() is MasterReviewOutcome.PRE_EXECUTION_REVIEW_READY
def test_warning_blocked(): assert make(blocked_items=("db",)).outcome() is MasterReviewOutcome.PRE_EXECUTION_REVIEW_READY_WITH_WARNINGS; assert make(review_digest="").outcome() is MasterReviewOutcome.PRE_EXECUTION_REVIEW_BLOCKED
def test_guard(): assert make(execution_permission=True).outcome() is MasterReviewOutcome.PRE_EXECUTION_REVIEW_NOT_READY
