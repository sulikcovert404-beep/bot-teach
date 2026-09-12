from app.services.delivery_wave_preparation_package import DeliveryWavePreparationPackage, Outcome


def make(**kw):
    b=dict(wave_scope=("wave1",), selected_capabilities=("rag",), exclusions=("deploy",), success_criteria=("pass",),
           technical_prerequisites=("contracts",), dependency_readiness=("ready",), test_requirements=("unit",),
           acceptance_preparation=("review",), planned_change_boundaries=("service",), rollback_expectations=("revert",),
           wave_rationale="value", trace_reference="t")
    b.update(kw); return DeliveryWavePreparationPackage(**b)


def test_ready_and_immutable():
    p=make(); assert p.outcome() is Outcome.READY
    try: p.trace_reference="x"; assert False
    except AttributeError: pass


def test_blocked_and_guard():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(deployment=True).outcome() is Outcome.INCOMPLETE


def test_warning_and_missing():
    assert make(remaining_blockers=("pg",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(wave_scope=()).outcome() is Outcome.INCOMPLETE
