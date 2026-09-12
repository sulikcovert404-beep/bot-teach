from app.services.production_integration_readiness_review import Outcome, ProductionIntegrationReadinessReview


def make(**overrides):
    names = ("data_ownership", "access_enforcement", "lifecycle_consistency", "execution_sequence",
             "prerequisite_chain", "ownership_risks", "permission_risks", "data_integrity_risks",
             "monitoring", "incident_handling", "recovery")
    values = {name: ("ok",) for name in names}; values.update(decision="PLAN", trace_reference="trace")
    values.update(overrides); return ProductionIntegrationReadinessReview(**values)


def test_ready_and_immutable():
    value = make(); assert value.outcome() is Outcome.READY
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_deferred():
    assert make(warnings=("production",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(data_ownership=()).outcome() is Outcome.DEFERRED


def test_blockers_and_guards():
    assert make(blockers=("db",)).outcome() is Outcome.BLOCKED
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(permission_change=True).outcome() is Outcome.BLOCKED
