from app.services.capability_wave_transition_review import CapabilityWaveTransitionReview, Outcome


def make(**kw):
    b={"delivered_capability":"rag", "achieved_objectives":("done",), "quality_status":("green",), "successful_patterns":("pattern",), "reusable_contracts":("contract",), "readiness_conditions":("ready",), "selection_rules":("rule",), "dependency_check":("checked",), "decision":"closed", "trace_reference":"t"}
    b.update(kw); return CapabilityWaveTransitionReview(**b)


def test_closed_and_immutable():
    p=make(); assert p.outcome() is Outcome.CLOSED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(new_capability_execution=True).outcome() is Outcome.OPEN


def test_actions_and_missing():
    assert make(deferred_items=("threshold",)).outcome() is Outcome.CLOSED_WITH_ACTIONS
    assert make(decision="").outcome() is Outcome.OPEN
