from app.services.content_integration_readiness_review import (
    ContentIntegrationReadinessReview,
    Outcome,
)


def make(**overrides):
    values = dict(storage_requirements=("versioned",), data_lifecycle=("retire",),
                  compatibility_impact=("isolated",), ownership_model=("admin",),
                  access_boundaries=("service",), permission_requirements=("review",),
                  affected_modules=("content",), contracts=("content-contract",),
                  risks=("consistency",), decision="DEFERRED", trace_reference="trace")
    values.update(overrides)
    return ContentIntegrationReadinessReview(**values)


def test_ready_and_immutable():
    review = make()
    assert review.outcome() is Outcome.READY
    try:
        review.decision = "x"
        assert False
    except AttributeError:
        pass


def test_warnings_and_deferred():
    assert make(warnings=("PG blocked",)).outcome() is Outcome.READY_WITH_WARNINGS
    assert make(contracts=()).outcome() is Outcome.DEFERRED


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(database_change=True).outcome() is Outcome.BLOCKED
