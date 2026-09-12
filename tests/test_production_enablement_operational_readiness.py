from app.services.production_enablement_operational_readiness import (
    OperationalOutcome, OperationalReadinessPackage,
)


def make(**overrides):
    fields = (
        "activation_boundary", "runtime_ownership", "stop_conditions",
        "identity_provider_path", "credential_lifecycle", "secret_boundaries",
        "health_signals", "audit_visibility", "failure_detection",
        "incident_ownership", "recovery_flow", "rollback_triggers",
        "activation_sequence",
    )
    values = {field: ("documented",) for field in fields}
    values.update(decision="PASS", trace_reference="trace")
    values.update(overrides)
    return OperationalReadinessPackage(**values)


def test_ready_and_immutable():
    package = make()
    assert package.outcome() is OperationalOutcome.READY
    try:
        package.decision = "changed"
        assert False
    except AttributeError:
        pass


def test_warning_and_deferred():
    assert make(warnings=("identity pending",)).outcome() is OperationalOutcome.READY_WITH_WARNINGS
    assert make(health_signals=()).outcome() is OperationalOutcome.DEFERRED


def test_activation_and_missing_trace_are_blocked():
    assert make(trace_reference="").outcome() is OperationalOutcome.BLOCKED
    assert make(runtime_activation=True).outcome() is OperationalOutcome.BLOCKED
