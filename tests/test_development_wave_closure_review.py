from app.services.development_wave_closure_review import DevelopmentWaveClosureReview, Outcome


def make(**kw):
    b={"delivered_changes": ("rag",), "achieved_objectives": ("objective",), "test_coverage": ("5 passed",), "validation_results": ("green",), "regression_assessment": ("safe",), "decision": "closed", "trace_reference": "t"}
    b.update(kw); return DevelopmentWaveClosureReview(**b)


def test_closed_and_immutable():
    p=make(); assert p.outcome() is Outcome.CLOSED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(new_feature_execution=True).outcome() is Outcome.NOT_CLOSED


def test_actions_and_missing():
    assert make(unresolved_items=("conflict",)).outcome() is Outcome.CLOSED_WITH_ACTIONS
    assert make(decision="").outcome() is Outcome.NOT_CLOSED
