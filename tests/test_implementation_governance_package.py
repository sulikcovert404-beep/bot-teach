from app.services.implementation_governance_package import ImplementationGovernancePackage, Outcome


def make(**kw):
    b={"coding_boundaries": ("scope",), "review_ownership": ("reviewer",), "change_ownership": ("owner",),
           "validation_requirements": ("tests",), "test_expectations": ("unit",), "change_proposal": ("request",),
           "completion_criteria": ("pass",), "defect_classification": ("severity",), "developer_handoff": ("handoff",),
           "acceptance_boundary": ("acceptance",), "trace_reference": "t"}
    b.update(kw); return ImplementationGovernancePackage(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(feature_execution=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(warnings=("risk",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(change_proposal=()).outcome() is Outcome.INCOMPLETE
