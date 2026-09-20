from app.services.development_readiness_gate_package import DevelopmentReadinessGatePackage, Outcome


def make(**kw):
    b={"tooling_assumptions": ("python",), "workspace_requirements": ("repo",), "dependency_readiness": ("ok",),
           "coding_workflow": ("branch",), "review_process": ("review",), "validation_process": ("tests",),
           "test_readiness": ("ready",), "acceptance_readiness": ("criteria",), "ownership": ("team",),
           "responsibility": ("executor",), "prerequisites": ("scope",), "trace_reference": "t"}
    b.update(kw); return DevelopmentReadinessGatePackage(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_forbidden():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(feature_implementation=True).outcome() is Outcome.NOT_READY


def test_warning_and_missing():
    assert make(blockers=("dependency",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(prerequisites=()).outcome() is Outcome.NOT_READY
