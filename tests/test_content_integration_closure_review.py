from app.services.content_integration_closure_review import Outcome, ContentIntegrationClosureReview


def make(**overrides):
    values = dict(implementation_outcome="COMPLETE", validation_result="VALIDATED_WITH_WARNINGS",
                  warning_register=("production gap",), lessons_learned=("boundary",),
                  future_entry_criteria=("external persistence",), trace_reference="trace")
    values.update(overrides); return ContentIntegrationClosureReview(**values)


def test_closed_with_actions_and_immutable():
    value = make(); assert value.outcome() is Outcome.CLOSED_WITH_ACTIONS
    try: value.validation_result = "x"; assert False
    except AttributeError: pass


def test_closed_without_warnings():
    assert make(warning_register=()).outcome() is Outcome.CLOSED


def test_open_and_blocked():
    assert make(lessons_learned=()).outcome() is Outcome.OPEN
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(database_change=True).outcome() is Outcome.BLOCKED
