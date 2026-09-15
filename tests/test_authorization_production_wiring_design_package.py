from app.services.authorization_production_wiring_design_package import (
    AuthorizationProductionWiringDesignPackage,
    Outcome,
)


def make(**overrides):
    names = ("identity_flow", "identity_contract", "ownership_resolution", "permission_evaluation",
             "access_matrix", "role_enforcement", "credential_boundary", "secret_handling",
             "audit_trail", "existing_behavior_preservation", "migration_risks", "security_validation",
             "failure_handling", "rollback_strategy")
    values = {name: ("ok",) for name in names}; values.update(decision="PLAN", trace_reference="trace")
    values.update(overrides); return AuthorizationProductionWiringDesignPackage(**values)


def test_designed_and_immutable():
    value = make(); assert value.outcome() is Outcome.DESIGNED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_incomplete():
    assert make(warnings=("security review",)).outcome() is Outcome.DESIGNED_WITH_WARNINGS
    assert make(identity_flow=()).outcome() is Outcome.INCOMPLETE


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(permission_change=True).outcome() is Outcome.BLOCKED
