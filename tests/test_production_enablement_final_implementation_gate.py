from app.services.production_enablement_final_implementation_gate import (
    Outcome,
    ProductionEnablementFinalImplementationGate,
)


def make(**overrides):
    names = ("approved_changes", "excluded_changes", "readiness", "data_risks",
             "security_risks", "operational_risks", "recovery_readiness")
    values = {name: ("ok",) for name in names}; values.update(rollback_ownership="ops", decision="REVIEW", trace_reference="trace")
    values.update(overrides); return ProductionEnablementFinalImplementationGate(**values)


def test_approved_and_immutable():
    value = make(); assert value.outcome() is Outcome.APPROVED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_conditions_and_deferred():
    assert make(conditions=("manual",)).outcome() is Outcome.APPROVED_WITH_CONDITIONS
    assert make(readiness=()).outcome() is Outcome.DEFERRED


def test_blockers_and_guards():
    assert make(blockers=("PG",)).outcome() is Outcome.BLOCKED
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(implementation_permission=True).outcome() is Outcome.BLOCKED
