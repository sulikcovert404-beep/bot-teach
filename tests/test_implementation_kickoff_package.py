from app.services.implementation_kickoff_package import ImplementationKickoffPackage, Outcome


def make(**kw):
    b={"wave_objective": "deliver", "scope_boundary": ("service",), "expected_deliverables": ("code",), "work_items": ("item",),
           "dependencies": ("deps",), "ownership": ("owner",), "prerequisites": ("ready",), "required_reviews": ("review",),
           "validation_checkpoints": ("tests",), "done_criteria": ("pass",), "quality_gates": ("gate",), "handoff_conditions": ("handoff",),
           "decision": "approved", "next_action": "start", "trace_reference": "t"}
    b.update(kw); return ImplementationKickoffPackage(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(feature_execution=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(blockers=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(decision="").outcome() is Outcome.INCOMPLETE
