from app.services.production_readiness_assessment import Outcome, ProductionReadinessAssessment


def make(**overrides):
    names = ("storage_options", "durability_requirements", "migration_readiness",
             "identity_boundary", "permission_architecture", "security_requirements",
             "monitoring_needs", "failure_handling", "rollback_requirements",
             "deferred_items", "implementation_order")
    values = {name: ("ok",) for name in names}; values.update(decision="PREPARE", trace_reference="trace")
    values.update(overrides); return ProductionReadinessAssessment(**values)


def test_ready_and_immutable():
    value = make(); assert value.outcome() is Outcome.READY
    try: value.decision = "x"; assert False
    except AttributeError: pass


def test_preparation_and_warnings():
    assert make(critical_blockers=("PG unavailable",)).outcome() is Outcome.PREPARATION_REQUIRED
    assert make(warnings=("non-production adapter",)).outcome() is Outcome.READY_WITH_WARNINGS


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(deployment=True).outcome() is Outcome.BLOCKED
