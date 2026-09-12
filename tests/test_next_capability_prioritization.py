from app.services.next_capability_prioritization import NextCapabilityPrioritization, Outcome


def make(**kw):
    b=dict(available_capabilities=("search", "admin"), business_technical_value=("value",), dependencies=("deps",), impact=("high",), complexity=("low",), risk=("low",), dependency_weight=("low",), rag_dependency=("none",), architecture_fit=("fit",), existing_contracts=("rag",), selected_capability="search", rationale="value", approved_next_wave="search", prerequisites=("ready",), trace_reference="t")
    b.update(kw); return NextCapabilityPrioritization(**b)


def test_selected_and_immutable():
    p=make(); assert p.outcome() is Outcome.SELECTED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(new_capability_execution=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_invalid():
    assert make(blockers=("risk",)).outcome() is Outcome.SELECTED_WITH_WARNINGS
    assert make(selected_capability="unknown").outcome() is Outcome.INCOMPLETE
