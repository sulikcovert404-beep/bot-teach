from app.services.content_integration_implementation_authorization_review import (
    ContentIntegrationImplementationAuthorizationReview,
    Outcome,
)


def make(**overrides):
    names = ("persistence_design", "authorization_design", "contracts", "dependencies",
             "required_changes", "migration_requirements", "data_risks", "security_risks",
             "compatibility_risks", "allowed_changes", "forbidden_changes", "rollback_requirements")
    values = {name: ("ok",) for name in names}; values.update(decision="DEFERRED", trace_reference="trace")
    values.update(overrides); return ContentIntegrationImplementationAuthorizationReview(**values)


def test_ready_and_immutable():
    review = make(); assert review.outcome() is Outcome.READY
    try: review.decision = "x"; assert False
    except AttributeError: pass


def test_deferred_and_warnings():
    assert make(contracts=()).outcome() is Outcome.DEFERRED
    assert make(warnings=("external dependency",)).outcome() is Outcome.READY_WITH_WARNINGS


def test_guards_block():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED
    assert make(database_change=True).outcome() is Outcome.BLOCKED
