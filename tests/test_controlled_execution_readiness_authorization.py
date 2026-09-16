from app.services.controlled_execution_readiness_authorization import (
    ControlledExecutionReadinessAuthorization,
    Outcome,
)


def make(**overrides):
    names = ("allowed_execution_scope", "forbidden_actions", "rollback_authority",
             "required_environments", "configuration_readiness", "dependency_availability",
             "credential_requirements", "permission_ownership", "approval_chain",
             "monitoring_activation", "incident_path", "recovery_ownership")
    values = {name: ("ok",) for name in names}; values.update(decision="REVIEW", trace_reference="trace")
    values.update(overrides); return ControlledExecutionReadinessAuthorization(**values)


def test_authorized_and_immutable():
    value = make(); assert value.outcome() is Outcome.AUTHORIZED
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_conditions_and_deferred():
    assert make(conditions=("manual gate",)).outcome() is Outcome.AUTHORIZED_WITH_CONDITIONS
    assert make(approval_chain=()).outcome() is Outcome.DEFERRED


def test_blockers_and_guards():
    assert make(blockers=("env",)).outcome() is Outcome.BLOCKED
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(execution_permission=True).outcome() is Outcome.BLOCKED
