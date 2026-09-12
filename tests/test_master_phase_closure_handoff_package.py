from app.services.master_phase_closure_handoff_package import *
def make(**o):
 d=dict(package_id="p",governance_closure_summary="closed",operational_readiness_summary="closed",transition_certification_summary="certified",master_review_result="ready",remaining_restrictions=("runtime prohibited",),next_phase_entry_conditions=("commander approval",),trace_reference="t",package_digest="d"); d.update(o); return MasterPhaseClosureHandoffPackage(**d)
def test_closed_warning(): assert make().outcome() is PhaseClosureOutcome.PHASE_CLOSED_WITH_WARNINGS
def test_blocked(): assert make(package_digest="").outcome() is PhaseClosureOutcome.PHASE_BLOCKED
def test_open_guard(): assert make(execution=True).outcome() is PhaseClosureOutcome.PHASE_OPEN
