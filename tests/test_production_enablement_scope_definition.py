from app.services.production_enablement_scope_definition import (
    Outcome,
    ProductionEnablementScopeDefinition,
)


def make(**overrides):
    names = ("production_capability", "out_of_scope", "storage_target", "migration_boundary",
             "rollback_requirements", "identity_integration", "permission_rollout",
             "activation_boundary", "operational_ownership", "success_criteria",
             "safety_gates", "stop_conditions")
    values = {name: ("ok",) for name in names}; values.update(decision="PLAN", trace_reference="trace")
    values.update(overrides); return ProductionEnablementScopeDefinition(**values)


def test_defined_and_immutable():
    value = make(); assert value.outcome() is Outcome.DEFINED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_incomplete():
    assert make(warnings=("manual",)).outcome() is Outcome.DEFINED_WITH_WARNINGS
    assert make(storage_target=()).outcome() is Outcome.INCOMPLETE


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(production_execution=True).outcome() is Outcome.BLOCKED
