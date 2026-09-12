from app.services.persistence_foundation_validation import Outcome, PersistenceFoundationValidation


def make(**overrides):
    names = ("creator_isolation", "snapshot_stability", "ordering_guarantees", "backward_compatibility",
             "regression_tests", "contract_preservation", "deterministic_behavior", "in_memory_limitation",
             "production_storage_gap", "migration_readiness")
    values = {name: ("ok",) for name in names}; values.update(decision="PASS", trace_reference="trace")
    values.update(overrides); return PersistenceFoundationValidation(**values)


def test_validated_and_immutable():
    value = make(); assert value.outcome() is Outcome.VALIDATED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_failure():
    assert make(warnings=("production",)).outcome() is Outcome.VALIDATED_WITH_WARNINGS
    assert make(snapshot_stability=()).outcome() is Outcome.FAILED


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(database_change=True).outcome() is Outcome.BLOCKED
