from app.services.first_development_wave_implementation_authorization_review import (
    FirstDevelopmentWaveImplementationAuthorizationReview,
    Outcome,
)


def make(**kw):
    b={"selected_capability": "rag", "boundary_verification": ("scope",), "dependency_readiness": ("ready",), "acceptance_readiness": ("criteria",), "quality_gate_readiness": ("tests",), "expected_files": ("module",), "affected_boundaries": ("service",), "risk_assessment": ("low",), "decision": "ready", "trace_reference": "t"}
    b.update(kw); return FirstDevelopmentWaveImplementationAuthorizationReview(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_permission_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(implementation_permission=True).outcome() is Outcome.BLOCKED


def test_warning_and_missing():
    assert make(blockers=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(decision="").outcome() is Outcome.BLOCKED
