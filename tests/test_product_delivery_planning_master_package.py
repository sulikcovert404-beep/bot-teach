from app.services.product_delivery_planning_master_package import (
    Outcome,
    ProductDeliveryPlanningMasterPackage,
)


def make(**kw):
    b=dict(capability_priorities=("rag",), delivery_sequence=("phase1",), milestone_grouping=("m1",),
           workstreams=("backend",), dependency_ordering=("contracts",), release_boundaries=("internal",),
           acceptance_gates=("review",), quality_checkpoints=("tests",), recommended_next_phase="scope-1",
           trace_reference="t")
    b.update(kw); return ProductDeliveryPlanningMasterPackage(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(runtime_execution=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(warnings=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(workstreams=()).outcome() is Outcome.INCOMPLETE
