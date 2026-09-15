from app.services.content_integration_design_package import ContentIntegrationDesignPackage, Outcome


def make(**overrides):
    fields = {name: ("ok",) for name in (
        "data_model_requirements", "storage_contract", "lifecycle_states", "consistency_rules",
        "migration_impact", "permission_model", "ownership_rules", "access_matrix",
        "security_boundaries", "component_interaction", "dependency_flow", "interface_contracts",
        "validation_strategy", "rollback_considerations", "failure_handling")}
    fields.update(decision="DEFERRED", trace_reference="trace")
    fields.update(overrides)
    return ContentIntegrationDesignPackage(**fields)


def test_designed_and_immutable():
    package = make()
    assert package.outcome() is Outcome.DESIGNED
    try:
        package.decision = "x"
        assert False
    except AttributeError:
        pass


def test_warnings_and_incomplete():
    assert make(warnings=("PG readiness",)).outcome() is Outcome.DESIGNED_WITH_WARNINGS
    assert make(storage_contract=()).outcome() is Outcome.INCOMPLETE


def test_design_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(migration_execution=True).outcome() is Outcome.BLOCKED
