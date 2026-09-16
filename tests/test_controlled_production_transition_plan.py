from app.services.controlled_production_transition_plan import (
    ControlledProductionTransitionPlan,
    Outcome,
)


def make(**overrides):
    names = ("rollout_model", "entry_criteria", "exit_criteria", "storage_migration",
             "rollback_strategy", "validation_checkpoints", "identity_integration",
             "permission_rollout", "security_gates", "monitoring", "incident_handling",
             "recovery_process")
    values = {name: ("ok",) for name in names}; values.update(decision="PREPARE", trace_reference="trace")
    values.update(overrides); return ControlledProductionTransitionPlan(**values)


def test_ready_and_immutable():
    plan = make(); assert plan.outcome() is Outcome.READY
    try: plan.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_incomplete():
    assert make(warnings=("staging",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(monitoring=()).outcome() is Outcome.BLOCKED


def test_execution_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(migration_execution=True).outcome() is Outcome.BLOCKED
