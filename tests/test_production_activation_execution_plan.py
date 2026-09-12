from app.services.production_activation_execution_plan import (
    ActivationExecutionPlan, ActivationPlanOutcome,
)


def make(**overrides):
    fields = (
        "activation_sequence", "dependency_order", "checkpoints", "allowed_actions",
        "forbidden_actions", "stop_conditions", "migration_steps",
        "validation_checkpoints", "rollback_points", "identity_rollout",
        "credential_handling", "security_checks", "execution_record_template",
    )
    values = {field: ("defined",) for field in fields}
    values.update(decision="PASS", trace_reference="trace")
    values.update(overrides)
    return ActivationExecutionPlan(**values)


def test_ready_and_immutable():
    plan = make()
    assert plan.outcome() is ActivationPlanOutcome.READY
    try:
        plan.decision = "changed"
        assert False
    except AttributeError:
        pass


def test_warning_and_deferred():
    assert make(warnings=("external dependency",)).outcome() is ActivationPlanOutcome.READY_WITH_WARNINGS
    assert make(rollback_points=()).outcome() is ActivationPlanOutcome.DEFERRED


def test_execution_guards_block():
    assert make(trace_reference="").outcome() is ActivationPlanOutcome.BLOCKED
    assert make(migration_execution=True).outcome() is ActivationPlanOutcome.BLOCKED
