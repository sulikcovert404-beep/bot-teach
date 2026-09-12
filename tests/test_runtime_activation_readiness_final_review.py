import pytest

from app.services.runtime_activation_readiness_final_review import RuntimeActivationReadinessFinalReview, FinalReviewOutcome


def make_review(**kwargs):
    base = dict(review_id="r1", readiness_assurance_bundle_reference="bundle:1", readiness_baseline_freeze_reference="freeze:1", governance_closure_reference="closure:1", activation_control_plane_reference="control:1", activation_decision_reference="decision:1", cross_layer_findings=(), boundary_assertions=("runtime prohibited",), trace_reference="trace:1")
    base.update(kwargs)
    return RuntimeActivationReadinessFinalReview(**base)


def test_immutable_and_digest_bound():
    review = make_review()
    assert review.review_digest == review.canonical_digest()
    with pytest.raises((AttributeError, TypeError)):
        review.review_id = "x"


def test_precedence_and_outcomes():
    assert RuntimeActivationReadinessFinalReview.evaluate(references=("BLOCKED",)) is FinalReviewOutcome.FINAL_BLOCKED
    assert RuntimeActivationReadinessFinalReview.evaluate(references=("INVALID",)) is FinalReviewOutcome.FINAL_NOT_READY
    assert RuntimeActivationReadinessFinalReview.evaluate(references=("UNKNOWN",)) is FinalReviewOutcome.UNKNOWN
    assert RuntimeActivationReadinessFinalReview.evaluate(references=("ok",), findings=("warning",)) is FinalReviewOutcome.FINAL_READY_WITH_WARNINGS
    assert RuntimeActivationReadinessFinalReview.evaluate(references=("ok",)) is FinalReviewOutcome.FINAL_READY


def test_tamper_and_secret_rejected():
    with pytest.raises(ValueError):
        make_review(review_digest="bad")
    with pytest.raises(ValueError):
        make_review(trace_reference="password=bad")
