from dataclasses import FrozenInstanceError

import pytest

from app.services.execution_contract import ExecutionOutcome, ExecutionRequest, execute


def ctx(**overrides):
    value = {"decision_reference": "d1", "command_reference": "c1", "actor_reference": "a1",
             "digest_reference": "sha256:x", "started_at": "2026-01-01T00:00:00Z"}
    value.update(overrides)
    return value


def test_approved_execution_is_pure_completed_intent():
    result = execute("APPROVED", ctx())
    assert result.outcome is ExecutionOutcome.COMPLETED
    assert result.result_reference.startswith("execution:")


@pytest.mark.parametrize("decision", ["DENIED", "BLOCKED", "REQUIRES_REVIEW", "CONFLICT"])
def test_non_approved_decisions_are_not_executed(decision):
    assert execute(decision, ctx()).outcome is ExecutionOutcome.NOT_EXECUTED


def test_cancellation_and_digest_mismatch():
    assert execute("APPROVED", ctx(cancelled=True)).outcome is ExecutionOutcome.CANCELLED
    assert execute("APPROVED", ctx(expected_digest="other")).outcome is ExecutionOutcome.FAILED


def test_request_is_immutable_and_unicode_round_trips():
    request = ExecutionRequest.from_context(ctx(actor_reference="دانش\u200cآموز", execution_id="e1"))
    assert "\u200c" in request.actor_reference
    with pytest.raises(FrozenInstanceError):
        request.actor_reference = "x"
    assert request.canonical_json() == ExecutionRequest.from_context(ctx(actor_reference="دانش\u200cآموز", execution_id="e1")).canonical_json()
