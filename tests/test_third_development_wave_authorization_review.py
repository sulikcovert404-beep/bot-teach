from app.services.third_development_wave_authorization_review import (
    Outcome, ThirdDevelopmentWaveAuthorizationReview,
)


def make(**overrides):
    values = dict(capability="content", objective="manage content",
                  boundaries=("service",), exclusions=("runtime",),
                  existing_modules=("content_service",), contracts=("content-contract",),
                  expected_files=("app/services/content.py",),
                  acceptance_criteria=("deterministic",), test_strategy=("unit",),
                  validation_requirements=("pytest",), trace_reference="trace")
    values.update(overrides)
    return ThirdDevelopmentWaveAuthorizationReview(**values)


def test_ready_and_immutable():
    review = make()
    assert review.outcome() is Outcome.READY
    try:
        review.capability = "x"
        assert False
    except AttributeError:
        pass


def test_warnings_are_explicit():
    assert make(warnings=("external dependency",)).outcome() is Outcome.READY_WITH_WARNINGS


def test_missing_or_side_effect_guard_blocks():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(implementation_permission=True).outcome() is Outcome.BLOCKED
    assert make(acceptance_criteria=()).outcome() is Outcome.BLOCKED
