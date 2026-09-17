from app.services.rag_integration_impact_review_wave import Outcome, RAGIntegrationImpactReviewWave


def make(**kw):
    b=dict(consumers=("tutor",), downstream_behavior=("ground",), compatibility_boundaries=("legacy",), affected_interfaces=("GroundedContext",), required_updates=("tests",), backward_compatibility=("preserve",), existing_tests=("rag",), missing_scenarios=("conflict",), future_regression_needs=("threshold",), approved_decision="ready", trace_reference="t")
    b.update(kw); return RAGIntegrationImpactReviewWave(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(provider_change=True).outcome() is Outcome.BLOCKED


def test_warning_and_missing():
    assert make(deferred_changes=("runtime",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(approved_decision="").outcome() is Outcome.BLOCKED
