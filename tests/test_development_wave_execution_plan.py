from app.services.development_wave_execution_plan import DevelopmentWaveExecutionPlan, Outcome


def make(**kw):
    b={"selected_work_packages": ("pkg",), "implementation_sequence": ("step",), "milestones": ("m1",), "technical_tasks": ("task",),
           "dependencies": ("dep",), "expected_outputs": ("out",), "unit_test_expectations": ("test",), "review_checkpoints": ("review",),
           "acceptance_flow": ("accept",), "completion_criteria": ("done",), "handoff_requirements": ("handoff",), "closure_conditions": ("close",), "trace_reference": "t"}
    b.update(kw); return DevelopmentWaveExecutionPlan(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(feature_execution=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(blockers=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(milestones=()).outcome() is Outcome.INCOMPLETE
