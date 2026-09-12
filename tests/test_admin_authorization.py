from app.services.admin_authorization import (
    Actor, AuthorizationContext, PrincipalType, Role, authorize,
)
from app.services.content_commands import SubmitProcessingCommand, PublishRequestContract


def _submit() -> SubmitProcessingCommand:
    return SubmitProcessingCommand(idempotency_key="k", request_hash="h", content_version_id=1)


def test_creator_can_submit_own_draft() -> None:
    decision = authorize(_submit(), Actor("u1", frozenset({Role.CREATOR})), AuthorizationContext("u1", "DRAFT"))
    assert decision.allowed and decision.reason_code is None


def test_owner_mismatch_is_denied_deterministically() -> None:
    actor = Actor("u2", frozenset({Role.CREATOR}))
    context = AuthorizationContext("u1", "DRAFT")
    assert authorize(_submit(), actor, context) == authorize(_submit(), actor, context)
    assert authorize(_submit(), actor, context).reason_code == "invalid_ownership"


def test_reviewer_cannot_self_approve() -> None:
    command = PublishRequestContract(idempotency_key="k", request_hash="h", content_version_id=1, expected_version=1)
    decision = authorize(command, Actor("u1", frozenset({Role.REVIEWER})), AuthorizationContext("u1", "APPROVED"))
    assert decision.reason_code == "missing_role"


def test_publisher_requires_approved_state() -> None:
    command = PublishRequestContract(idempotency_key="k", request_hash="h", content_version_id=1, expected_version=1)
    decision = authorize(command, Actor("p", frozenset({Role.PUBLISHER})), AuthorizationContext("u1", "VALIDATED"))
    assert not decision.allowed and decision.reason_code == "forbidden_transition"


def test_service_principal_is_rejected() -> None:
    decision = authorize(_submit(), Actor("svc", frozenset({Role.CREATOR}), PrincipalType.SERVICE), AuthorizationContext())
    assert decision.reason_code == "invalid_actor"
