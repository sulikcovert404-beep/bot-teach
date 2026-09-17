from app.services.third_development_wave_capability_selection import (
    Outcome,
    ThirdDevelopmentWaveCapabilitySelection,
)


def make(**kw):
    b=dict(available_capabilities=("content", "analytics"), business_technical_value=("value",), dependencies=("none",), impact=("high",), complexity=("low",), risk=("low",), architectural_fit=("fit",), existing_contracts=("contracts",), rag_dependency=("none",), implementation_isolation=("isolated",), selected_capability="content", rationale="value", prerequisites=("ready",), trace_reference="t")
    b.update(kw); return ThirdDevelopmentWaveCapabilitySelection(**b)


def test_selected_and_immutable():
    p=make(); assert p.outcome() is Outcome.SELECTED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(deployment=True).outcome() is Outcome.BLOCKED


def test_invalid_selection():
    assert make(selected_capability="unknown").outcome() is Outcome.BLOCKED
    assert make(risk=()).outcome() is Outcome.BLOCKED
