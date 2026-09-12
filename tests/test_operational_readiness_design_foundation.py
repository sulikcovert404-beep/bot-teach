from app.services.operational_readiness_design_foundation import DesignOutcome, OperationalReadinessDesignFoundation


def make(**kw):
    data = dict(foundation_id="f1", governance_phase_closure_reference="g1", operational_scope_definition="design", future_capability_boundaries=("runtime",), dependency_inventory=(), risk_summary=(), readiness_constraints=("approval",), boundary_assertions={"runtime_activation":"PROHIBITED", "execution":False}, trace_reference="t1", foundation_digest="d1")
    data.update(kw)
    return OperationalReadinessDesignFoundation(**data)


def test_ready_and_immutable():
    f = make()
    assert f.outcome() is DesignOutcome.DESIGN_READY
    try:
        f.foundation_id = "x"
        assert False
    except FrozenInstanceError:
        pass


def test_blocked_without_trace():
    assert make(trace_reference="").outcome() is DesignOutcome.DESIGN_BLOCKED


def test_warning_for_risks():
    assert make(risk_summary=("dependency",)).outcome() is DesignOutcome.DESIGN_READY_WITH_WARNINGS


from dataclasses import FrozenInstanceError
