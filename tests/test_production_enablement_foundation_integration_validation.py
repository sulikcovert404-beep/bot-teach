from app.services.production_enablement_foundation_integration_validation import (
    FoundationIntegrationValidation, IntegrationOutcome,
)


def make(**overrides):
    fields = (
        "creator_ownership", "authorization_enforcement", "data_access_boundaries",
        "create_authorize_persist", "update_authorize_version_check", "deny_no_mutation",
        "unauthorized_access", "conflict_handling", "data_integrity", "content_regression",
        "commands_regression", "admin_authorization_regression", "curriculum_pipeline_regression",
        "identity_provider_gap", "credential_gap", "runtime_activation_gap",
    )
    values = {field: ("ok",) for field in fields}
    values.update(decision="PASS", trace_reference="trace")
    values.update(overrides)
    return FoundationIntegrationValidation(**values)


def test_validated_and_immutable():
    value = make()
    assert value.outcome() is IntegrationOutcome.VALIDATED
    try:
        value.decision = "changed"
        assert False
    except AttributeError:
        pass


def test_warning_and_missing_evidence():
    assert make(warnings=("runtime gap",)).outcome() is IntegrationOutcome.VALIDATED_WITH_WARNINGS
    assert make(conflict_handling=()).outcome() is IntegrationOutcome.FAILED


def test_guards_block():
    assert make(trace_reference="").outcome() is IntegrationOutcome.BLOCKED
    assert make(database_change=True).outcome() is IntegrationOutcome.BLOCKED
