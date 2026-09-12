from app.services.authorization_wiring_validation import Outcome, AuthorizationWiringValidation


def make(**overrides):
    names = ("allowed_path", "denied_path", "reason_consistency", "command_trace", "actor_trace",
             "policy_version", "deterministic_output", "existing_policy", "content_integration",
             "regression", "ownership_boundary", "access_enforcement", "failure_handling",
             "identity_provider_gap", "credential_gap", "production_permission_gap")
    values = {name: ("ok",) for name in names}; values.update(decision="PASS", trace_reference="trace")
    values.update(overrides); return AuthorizationWiringValidation(**values)


def test_validated_and_immutable():
    value = make(); assert value.outcome() is Outcome.VALIDATED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_failure():
    assert make(warnings=("provider",)).outcome() is Outcome.VALIDATED_WITH_WARNINGS
    assert make(actor_trace=()).outcome() is Outcome.FAILED


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(permission_change=True).outcome() is Outcome.BLOCKED
