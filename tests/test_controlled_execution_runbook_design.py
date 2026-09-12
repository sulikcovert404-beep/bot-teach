from app.services.controlled_execution_runbook_design import Outcome, ControlledExecutionRunbookDesign


def make(**overrides):
    names = ("ordered_steps", "checkpoints", "stop_conditions", "rollback_triggers",
             "recovery_sequence", "post_rollback_validation", "pre_checks", "post_checks",
             "failure_handling", "planned_actions", "evidence_fields", "decision_points")
    values = {name: ("ok",) for name in names}; values.update(execution_owner="executor", approval_owner="commander", incident_owner="ops", trace_reference="trace")
    values.update(overrides); return ControlledExecutionRunbookDesign(**values)


def test_ready_and_immutable():
    value = make(); assert value.outcome() is Outcome.READY
    try: value.execution_owner = "x"; assert False
    except AttributeError: pass


def test_warning_and_incomplete():
    assert make(warnings=("manual gate",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(checkpoints=()).outcome() is Outcome.INCOMPLETE


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(production_execution=True).outcome() is Outcome.BLOCKED
