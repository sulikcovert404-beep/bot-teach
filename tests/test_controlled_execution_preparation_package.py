from app.services.controlled_execution_preparation_package import Outcome, ControlledExecutionPreparationPackage


def make(**overrides):
    names = ("action_boundaries", "required_artifacts", "evidence_requirements",
             "decision_ownership", "approval_dependencies", "required_state",
             "prerequisites", "rollback_readiness", "failure_handling",
             "recovery_verification")
    values = {name: ("ok",) for name in names}; values.update(decision="PREPARE", trace_reference="trace")
    values.update(overrides); return ControlledExecutionPreparationPackage(**values)


def test_ready_and_immutable():
    value = make(); assert value.outcome() is Outcome.READY
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_deferred():
    assert make(warnings=("manual check",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(required_artifacts=()).outcome() is Outcome.DEFERRED


def test_blockers_and_guards():
    assert make(blockers=("env",)).outcome() is Outcome.BLOCKED
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(execution_permission=True).outcome() is Outcome.BLOCKED
