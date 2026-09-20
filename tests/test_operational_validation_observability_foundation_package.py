from app.services.operational_validation_observability_foundation_package import (
    OperationalValidationObservabilityFoundationPackage,
    Outcome,
)


def make(**kw):
    base = {"validation_layers": ("contract",), "validation_ownership": ("service",),
                "validation_criteria": ("evidence",), "metric_semantics": ("count",),
                "signal_categories": ("health",), "health_states": ("healthy",),
                "finding_lifecycle": ("open",), "trace_reference": "trace-1"}
    base.update(kw)
    return OperationalValidationObservabilityFoundationPackage(**base)


def test_ready_and_immutable():
    p = make()
    assert p.outcome() is Outcome.READY
    try:
        p.trace_reference = "x"
        assert False
    except AttributeError:
        pass


def test_blocked_without_trace():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED


def test_runtime_guard_and_warning():
    assert make(runtime_monitoring=True).outcome() is Outcome.INCOMPLETE
    assert make(blockers=("pending evidence",)).outcome() is Outcome.READY_WITH_WARNINGS
