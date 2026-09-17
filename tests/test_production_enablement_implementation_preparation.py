from app.services.production_enablement_implementation_preparation import (
    Outcome,
    ProductionEnablementImplementationPreparation,
)


def make(**overrides):
    names = ("change_list", "module_boundaries", "dependency_order", "migration_steps_draft",
             "validation_checkpoints", "rollback_checkpoints", "identity_integration_tasks",
             "permission_mapping_tasks", "deployment_sequence", "verification_steps", "stop_conditions")
    values = {name: ("ok",) for name in names}; values.update(decision="PREPARE", trace_reference="trace")
    values.update(overrides); return ProductionEnablementImplementationPreparation(**values)


def test_ready_and_immutable():
    value = make(); assert value.outcome() is Outcome.READY
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_blocked():
    assert make(warnings=("manual",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(change_list=()).outcome() is Outcome.BLOCKED


def test_execution_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(migration_execution=True).outcome() is Outcome.BLOCKED
