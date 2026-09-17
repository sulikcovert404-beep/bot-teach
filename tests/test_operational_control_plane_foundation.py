from app.services.operational_control_plane_foundation import (
    OperationalControlPlaneFoundation,
    Outcome,
)


def make(**kw):
    base = dict(control_architecture=("separation",), policy_evaluation_semantics=("advisory",),
                command_ownership=("commander",), workflow_boundaries=("design",),
                escalation_model=("review",), audit_boundary=("trace",), trace_reference="t1")
    base.update(kw)
    return OperationalControlPlaneFoundation(**base)


def test_ready_and_frozen():
    p = make()
    assert p.outcome() is Outcome.READY
    try:
        p.trace_reference = "x"
        assert False
    except AttributeError:
        pass


def test_blocked_without_trace():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED


def test_forbidden_runtime_and_warning():
    assert make(command_execution=True).outcome() is Outcome.INCOMPLETE
    assert make(blockers=("unresolved policy",)).outcome() is Outcome.READY_WITH_WARNINGS
