from app.services.second_development_wave_execution_scope_definition import (
    Outcome,
    SecondDevelopmentWaveExecutionScope,
)


def make(**kw):
    b={"capability": "search", "purpose": "score and classify retrieved results", "user_system_behavior": ("return grounded state",), "non_goals": ("provider changes",), "allowed_files": ("app/services/rag.py",), "input_contract": ("RetrievalRequest",), "output_contract": ("GroundedContext",), "error_contract": ("ValueError",), "compatibility_requirements": ("preserve NO_SOURCE",), "acceptance_criteria": ("low scores are explicit",), "required_tests": ("threshold",), "regression_tests": ("legacy",), "out_of_scope": ("deployment",), "trace_reference": "t"}
    b.update(kw); return SecondDevelopmentWaveExecutionScope(**b)


def test_defined_and_immutable():
    p=make(); assert p.outcome() is Outcome.DEFINED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(implementation_permission=True).outcome() is Outcome.BLOCKED


def test_warning_and_missing():
    assert make(warnings=("decision",)).outcome() is Outcome.DEFINED_WITH_WARNINGS
    assert make(output_contract=()).outcome() is Outcome.INCOMPLETE
