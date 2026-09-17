from app.services.second_development_wave_closure_review import (
    Outcome,
    SecondDevelopmentWaveClosureReview,
)


def make(**kw):
    b=dict(delivered_changes=("rag",), objective_achievement=("done",), scope_compliance=("within",), test_validation=("10 passed",), regression_status=("green",), compatibility_review=("safe",), reusable_patterns=("pattern",), decision="closed", trace_reference="t")
    b.update(kw); return SecondDevelopmentWaveClosureReview(**b)


def test_closed_and_immutable():
    p=make(); assert p.outcome() is Outcome.CLOSED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(new_feature_execution=True).outcome() is Outcome.OPEN


def test_actions_and_missing():
    assert make(carryover_risks=("threshold",)).outcome() is Outcome.CLOSED_WITH_ACTIONS
    assert make(decision="").outcome() is Outcome.OPEN
