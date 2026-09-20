from app.services.third_development_wave_validation import Outcome, ThirdDevelopmentWaveValidation


def make(**overrides):
    values = {"implementation_outcome": "ACCEPTED", "acceptance_criteria": ("criteria",),
                  "behavior_correctness": ("correct",), "test_coverage": ("covered",),
                  "regression_status": "PASS", "compatibility": ("compatible",),
                  "typed_result_consistency": ("consistent",), "deterministic_reasons": ("stable",),
                  "preserved_behavior": ("preserved",), "trace_reference": "trace"}
    values.update(overrides)
    return ThirdDevelopmentWaveValidation(**values)


def test_validated_and_immutable():
    validation = make()
    assert validation.outcome() is Outcome.VALIDATED
    try:
        validation.trace_reference = "x"
        assert False
    except AttributeError:
        pass


def test_warnings_and_failures():
    assert make(warnings=("deferred persistence",)).outcome() is Outcome.VALIDATED_WITH_WARNINGS
    assert make(implementation_outcome="REJECTED").outcome() is Outcome.FAILED
    assert make(test_coverage=()).outcome() is Outcome.FAILED


def test_validation_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(runtime_execution=True).outcome() is Outcome.BLOCKED
