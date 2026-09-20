from app.services.development_roadmap_rebalancing_review import (
    DevelopmentRoadmapRebalancingReview,
    Outcome,
)


def make(**kw):
    b={"completed_capabilities": ("rag",), "delivered_value": ("quality",), "pending_capabilities": ("admin",), "pending_dependencies": ("none",), "pending_priorities": ("medium",), "complexity": ("low",), "risk": ("low",), "expected_value": ("high",), "recommendation": "SELECT_NEW_CAPABILITY", "trace_reference": "t"}
    b.update(kw); return DevelopmentRoadmapRebalancingReview(**b)


def test_select_and_immutable():
    p=make(); assert p.outcome() is Outcome.SELECT
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(provider_change=True).outcome() is Outcome.BLOCKED


def test_rebalance_and_continue():
    assert make(recommendation="REBALANCE_REQUIRED").outcome() is Outcome.REBALANCE
    assert make(recommendation="CONTINUE_CURRENT_CAPABILITY").outcome() is Outcome.CONTINUE
