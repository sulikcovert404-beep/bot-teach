from app.services.production_transition_final_gate_review import Outcome, ProductionTransitionFinalGateReview


def make(**overrides):
    names = ("transition_plan", "rollback_plan", "validation_plan", "deferred_items",
             "authorization_readiness", "identity_boundaries", "credential_impact",
             "monitoring_readiness", "incident_response", "recovery_readiness")
    values = {name: ("ok",) for name in names}; values.update(decision="REVIEW", trace_reference="trace")
    values.update(overrides); return ProductionTransitionFinalGateReview(**values)


def test_approved_and_immutable():
    value = make(); assert value.outcome() is Outcome.APPROVED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_conditions_and_deferred():
    assert make(conditions=("manual approval",)).outcome() is Outcome.APPROVED_WITH_CONDITIONS
    assert make(validation_plan=()).outcome() is Outcome.DEFERRED


def test_blockers_and_guards():
    assert make(blockers=("PG",)).outcome() is Outcome.BLOCKED
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(production_execution=True).outcome() is Outcome.BLOCKED
