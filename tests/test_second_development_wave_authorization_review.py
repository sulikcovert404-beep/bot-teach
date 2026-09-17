from app.services.second_development_wave_authorization_review import (
    Outcome,
    SecondDevelopmentWaveAuthorizationReview,
)


def make(**kw):
    b=dict(capability_confirmation="search", scope_boundary=("service",), exclusions=("deploy",), existing_contracts=("rag",), required_prerequisites=("ready",), expected_modules=("search",), affected_areas=("api",), acceptance_criteria=("pass",), test_strategy=("unit",), validation_requirements=("green",), decision="ready", trace_reference="t")
    b.update(kw); return SecondDevelopmentWaveAuthorizationReview(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(implementation_permission=True).outcome() is Outcome.BLOCKED


def test_warning_and_missing():
    assert make(blockers=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(decision="").outcome() is Outcome.BLOCKED
