from app.services.architecture_program_closure_package import (
    ArchitectureProgramClosurePackage,
    Outcome,
)


def make(**kw):
    b = {"final_architecture_summary": ("summary",), "artifact_inventory": ("artifacts",),
         "dependency_closure": ("closed",), "risk_closure": ("risks",), "final_boundary_register": ("boundaries",),
         "future_phase_entry_criteria": ("scope",), "trace_reference": "t"}
    b.update(kw); return ArchitectureProgramClosurePackage(**b)


def test_closed_and_immutable():
    p=make(); assert p.outcome() is Outcome.CLOSED
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_open():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(execution=True).outcome() is Outcome.OPEN


def test_warning_and_missing():
    assert make(warnings=("open item",)).outcome() is Outcome.CLOSED_WITH_WARNINGS
    assert make(risk_closure=()).outcome() is Outcome.OPEN
