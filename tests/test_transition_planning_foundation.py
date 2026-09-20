from app.services.transition_planning_foundation import (
    TransitionOutcome,
    TransitionPlanningFoundation,
)


def make(**overrides):
    d={"foundation_id": "tp-1","current_phase_reference": "readiness","future_phase_boundary": "runtime",
    "transition_objectives": ("map",),"dependency_assumptions": ("pg readiness",),"change_categories": ("controlled",),"impact_classification": {"controlled":"bounded"},"risk_levels": {"controlled":"medium"},"required_review_boundaries": ("commander",),"rollback_scenarios": ("failed handoff",),"failure_categories": ("dependency",),"recovery_constraints": ("no runtime action",),"restore_boundaries": ("governance only",),"ownership_boundary": "commander","responsibility_transition": "executor","handoff_evidence_requirements": ("trace",),"review_package_scope": ("design",),"review_inputs": ("baseline",),"unresolved_items": (),"trace_reference": "trace-1","foundation_digest": "digest","execution": False,"transition_design_only": True}
    d.update(overrides); return TransitionPlanningFoundation(**d)

def test_ready(): assert make().outcome() is TransitionOutcome.TRANSITION_READY

def test_warnings_and_blocked():
    assert make(unresolved_items=("open",)).outcome() is TransitionOutcome.TRANSITION_READY_WITH_WARNINGS
    assert make(foundation_digest="").outcome() is TransitionOutcome.TRANSITION_BLOCKED

def test_incomplete_and_deterministic():
    x=make(rollback_scenarios=()); assert x.outcome() is TransitionOutcome.TRANSITION_INCOMPLETE
    assert make().canonical_payload()==make().canonical_payload()
