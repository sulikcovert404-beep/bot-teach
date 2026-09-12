from app.services.rag_quality_enhancement_wave import RAGQualityEnhancementWave, QualityOutcome


def make(**kw):
    b=dict(conflict_categories=("version",), resolution_rules=("report",), precedence_model=("approved",), threshold_strategy=("calibrate",), confidence_levels=("low",), scoring_interpretation=("score",), grounding_state_rules=("map",), explainability_metadata=("reason",), compatibility_rules=("legacy",), validation_scenarios=("case",), trace_reference="t")
    b.update(kw); return RAGQualityEnhancementWave(**b)


def test_enhanced_and_immutable():
    p=make(); assert p.outcome() is QualityOutcome.ENHANCED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is QualityOutcome.BLOCKED
    assert make(deployment=True).outcome() is QualityOutcome.INCOMPLETE


def test_warning_and_missing():
    assert make(blockers=("calibration",)).outcome() is QualityOutcome.ENHANCED_WITH_WARNINGS
    assert make(precedence_model=()).outcome() is QualityOutcome.INCOMPLETE
