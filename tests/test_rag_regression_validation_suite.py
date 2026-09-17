from app.services.rag_regression_validation_suite import Outcome, RAGRegressionValidationSuite


def make(**kw):
    b=dict(baseline_scenarios=("basic",), expected_grounding_states=("no_source",), failure_cases=("empty",), retrieval_request_validation=("limits",), source_guardian_behavior=("mapping",), confidence_outcomes=("low",), acceptance_criteria=("pass",), edge_cases=("rtl",), compatibility_checks=("legacy",), validated_behaviors=("threshold",), trace_reference="t")
    b.update(kw); return RAGRegressionValidationSuite(**b)


def test_stable_and_immutable():
    p=make(); assert p.outcome() is Outcome.STABLE
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(provider_change=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(deferred_risks=("conflict",)).outcome() is Outcome.STABLE_WITH_WARNINGS
    assert make(edge_cases=()).outcome() is Outcome.INCOMPLETE
