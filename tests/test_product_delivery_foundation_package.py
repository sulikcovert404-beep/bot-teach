from app.services.product_delivery_foundation_package import (
    Outcome,
    ProductDeliveryFoundationPackage,
)


def make(**kw):
    b = dict(capability_inventory=("rag",), feature_boundaries=("admin",), business_objectives=("education",),
             success_criteria=("verified",), delivery_streams=("backend",), component_ownership=("team",),
             implementation_roadmap=("phase1",), dependency_ordering=("contracts",), testing_strategy=("unit",),
             acceptance_criteria=("reviewed",), trace_reference="t")
    b.update(kw); return ProductDeliveryFoundationPackage(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(deployment=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(warnings=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(success_criteria=()).outcome() is Outcome.INCOMPLETE
