from app.services.third_development_wave_closure_review import Outcome, ThirdDevelopmentWaveClosureReview


def make(**overrides):
    values = dict(implementation_outcome="COMPLETE", validation_result="VALIDATED",
                  lessons_learned=("pure boundary",), carryover_risks=("persistence",),
                  next_capability_entry_criteria=("new scope",), trace_reference="trace")
    values.update(overrides)
    return ThirdDevelopmentWaveClosureReview(**values)


def test_closed_with_actions_and_immutable():
    review = make()
    assert review.outcome() is Outcome.CLOSED_WITH_ACTIONS
    try:
        review.validation_result = "x"
        assert False
    except AttributeError:
        pass


def test_closed_without_risks():
    assert make(carryover_risks=()).outcome() is Outcome.CLOSED


def test_open_and_blocked_guards():
    assert make(validation_result="FAILED").outcome() is Outcome.OPEN
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(runtime_execution=True).outcome() is Outcome.BLOCKED
