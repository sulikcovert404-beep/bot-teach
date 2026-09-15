from app.services.authorization_production_wiring_scope_definition import (
    AuthorizationProductionWiringScopeDefinition,
    Outcome,
)


def make(**overrides):
    names = ("identity_source", "identity_contract", "ownership_mapping", "permission_checks",
             "access_rules", "role_ownership_enforcement", "credential_boundary", "secret_handling",
             "audit_requirements", "existing_authorization_behavior", "regression_risks",
             "success_conditions", "failure_conditions", "rollback_boundary")
    values = {name: ("ok",) for name in names}; values.update(decision="PLAN", trace_reference="trace")
    values.update(overrides); return AuthorizationProductionWiringScopeDefinition(**values)


def test_defined_and_immutable():
    value = make(); assert value.outcome() is Outcome.DEFINED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_incomplete():
    assert make(warnings=("identity",)).outcome() is Outcome.DEFINED_WITH_WARNINGS
    assert make(permission_checks=()).outcome() is Outcome.INCOMPLETE


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(credential_change=True).outcome() is Outcome.BLOCKED
