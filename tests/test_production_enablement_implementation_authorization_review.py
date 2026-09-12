from app.services.production_enablement_implementation_authorization_review import Outcome, ProductionEnablementImplementationAuthorizationReview


def make(**overrides):
    names = ("storage_design", "migration_design", "authorization_design", "activation_design",
             "data_risks", "security_risks", "operational_risks", "rollback_risks",
             "allowed_actions", "forbidden_actions", "phase_separation")
    values = {name: ("ok",) for name in names}; values.update(execution_ownership="exec", approval_ownership="approve", incident_ownership="incident", decision="REVIEW", trace_reference="trace")
    values.update(overrides); return ProductionEnablementImplementationAuthorizationReview(**values)


def test_ready_and_immutable():
    value = make(); assert value.outcome() is Outcome.READY
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_warning_and_deferred():
    assert make(warnings=("manual",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(storage_design=()).outcome() is Outcome.DEFERRED


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(migration_execution=True).outcome() is Outcome.BLOCKED
