from app.services.first_development_wave_scope_selection import FirstDevelopmentWaveScopeSelection, Outcome


def make(**kw):
    b=dict(candidate_capabilities=("rag", "admin"), selected_capability="rag", priority_scoring=("value",), dependency_check=("ready",), implementation_boundary=("service",), acceptance_criteria=("tests",), trace_reference="t")
    b.update(kw); return FirstDevelopmentWaveScopeSelection(**b)


def test_selected_and_immutable():
    p=make(); assert p.outcome() is Outcome.SELECTED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(implementation_execution=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_invalid_choice():
    assert make(blockers=("risk",)).outcome() is Outcome.SELECTED_WITH_WARNINGS
    assert make(selected_capability="unknown").outcome() is Outcome.INCOMPLETE
