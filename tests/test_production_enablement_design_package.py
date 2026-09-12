from app.services.production_enablement_design_package import Outcome, ProductionEnablementDesignPackage


def make(**overrides):
    names = ("storage_architecture", "migration_strategy", "data_validation", "rollback_design",
             "identity_integration", "permission_mapping", "security_controls", "activation_sequence",
             "operational_ownership", "monitoring_model", "release_strategy", "checkpoints", "recovery_flow")
    values = {name: ("ok",) for name in names}; values.update(decision="PLAN", trace_reference="trace")
    values.update(overrides); return ProductionEnablementDesignPackage(**values)


def test_designed_and_immutable():
    value = make(); assert value.outcome() is Outcome.DESIGNED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_incomplete():
    assert make(warnings=("manual",)).outcome() is Outcome.DESIGNED_WITH_WARNINGS
    assert make(data_validation=()).outcome() is Outcome.INCOMPLETE


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(deployment=True).outcome() is Outcome.BLOCKED
