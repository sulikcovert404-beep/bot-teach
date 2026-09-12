from app.services.production_enablement_final_activation_gate import (
    ActivationOutcome, FinalActivationGateReview,
)


def make(**overrides):
    fields = (
        "foundation_status", "authorization_status", "operational_readiness",
        "activation_scope", "allowed_actions", "forbidden_actions",
        "identity_readiness", "credential_boundary", "secret_handling",
        "monitoring", "incident_response", "rollback_readiness",
    )
    values = {field: ("reviewed",) for field in fields}
    values.update(decision="PASS", trace_reference="trace")
    values.update(overrides)
    return FinalActivationGateReview(**values)


def test_approval_and_immutability():
    review = make()
    assert review.outcome() is ActivationOutcome.APPROVED
    try:
        review.decision = "changed"
        assert False
    except AttributeError:
        pass


def test_conditions_and_missing_readiness():
    assert make(conditions=("identity pending",)).outcome() is ActivationOutcome.APPROVED_WITH_CONDITIONS
    assert make(monitoring=()).outcome() is ActivationOutcome.DEFERRED


def test_execution_guards_block():
    assert make(trace_reference="").outcome() is ActivationOutcome.BLOCKED
    assert make(production_execution=True).outcome() is ActivationOutcome.BLOCKED
