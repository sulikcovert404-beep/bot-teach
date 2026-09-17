from app.services.rag_confidence_conflict_decision_wave import (
    Outcome,
    RAGConfidenceConflictDecisionWave,
)


def make(**kw):
    b=dict(conflict_detection_semantics=("version",), source_precedence_rules=("approved",), resolution_outcomes=("report",), confidence_bands=("low",), threshold_policy=("fixed",), scoring_interpretation=("retrieval",), valid_source=("sufficient",), low_confidence=("warn",), conflicting_sources=("escalate",), no_source=("refuse",), backward_compatibility=("preserve",), required_changes=("contract",), approved_semantics=("matrix",), future_implementation_boundary=("runtime",), trace_reference="t")
    b.update(kw); return RAGConfidenceConflictDecisionWave(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(provider_change=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(deferred_items=("calibration",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(no_source=()).outcome() is Outcome.INCOMPLETE
