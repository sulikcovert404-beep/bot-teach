from app.services.content_integration_validation import ContentIntegrationValidation, Outcome


def make(**overrides):
    names = ("create_flow", "update_flow", "ownership_enforcement", "conflict_handling",
             "persistence_adapter_contract", "authorization_contract", "typed_result_behavior",
             "existing_content_behavior", "command_compatibility", "api_compatibility",
             "in_memory_limitation", "migration_readiness", "production_gap")
    values = {name: ("ok",) for name in names}; values.update(decision="PASS", trace_reference="trace")
    values.update(overrides); return ContentIntegrationValidation(**values)


def test_validated_and_immutable():
    value = make(); assert value.outcome() is Outcome.VALIDATED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_failure():
    assert make(warnings=("production gap",)).outcome() is Outcome.VALIDATED_WITH_WARNINGS
    assert make(api_compatibility=()).outcome() is Outcome.FAILED


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(new_integration_execution=True).outcome() is Outcome.BLOCKED
