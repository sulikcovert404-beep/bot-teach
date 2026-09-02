import pytest

from app.services.pipeline_guards import (
    GuardViolation,
    PublicationCandidate,
    assert_idempotent_request,
    assert_pointer_cas,
    assert_publishable,
    assert_transition,
)


def candidate(**overrides):
    values = dict(version_id=1, processing_state="VALIDATED", review_state="APPROVED", vector_sync_state="VECTOR_SYNCED", pipeline_digest="d")
    values.update(overrides)
    return PublicationCandidate(**values)


def test_valid_processing_transition():
    assert_transition("processing", "UPLOADED", "PROCESSING")


def test_invalid_transition_is_rejected():
    with pytest.raises(GuardViolation):
        assert_transition("processing", "UPLOADED", "VALIDATED")


@pytest.mark.parametrize("field,value", [("review_state", "DRAFT"), ("vector_sync_state", "VECTOR_PENDING"), ("processing_state", "PROCESSING")])
def test_publish_requires_all_gates(field, value):
    with pytest.raises(GuardViolation):
        assert_publishable(candidate(**{field: value}))


def test_publish_checks_digest_and_pointer_cas():
    with pytest.raises(GuardViolation):
        assert_publishable(candidate(approval_digest="other"))
    with pytest.raises(GuardViolation):
        assert_pointer_cas(2, 1)


def test_idempotent_replay_and_key_reuse():
    assert assert_idempotent_request(None, "h") is False
    assert assert_idempotent_request("h", "h") is True
    with pytest.raises(GuardViolation):
        assert_idempotent_request("h", "different")

