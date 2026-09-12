from app.services.admin_authorization import Actor, AuthorizationContext, Role
from app.services.content_commands import SubmitProcessingCommand, ApproveContentVersionCommand, PublishRequestContract
from app.services.workflow_orchestration import WorkflowDispatcher, WorkflowStatus


def command(h="h"):
    return SubmitProcessingCommand(idempotency_key="k", request_hash=h, content_version_id=1)


def test_dispatch_accepts_and_replays() -> None:
    d = WorkflowDispatcher(); actor = Actor("u", frozenset({Role.CREATOR}))
    first = d.dispatch(command(), actor, AuthorizationContext("u", "DRAFT"))
    assert first.status is WorkflowStatus.ACCEPTED
    assert d.dispatch(command(), actor, AuthorizationContext("u", "DRAFT")) == first


def test_duplicate_key_with_new_payload_conflicts() -> None:
    d = WorkflowDispatcher(); actor = Actor("u", frozenset({Role.CREATOR}))
    d.dispatch(command(), actor, AuthorizationContext("u", "DRAFT"))
    result = d.dispatch(command("other"), actor, AuthorizationContext("u", "DRAFT"))
    assert result.status is WorkflowStatus.CONFLICT


def test_unauthorized_is_typed() -> None:
    result = WorkflowDispatcher().dispatch(command(), Actor("u", frozenset({Role.REVIEWER})), AuthorizationContext("u", "DRAFT"))
    assert result.status is WorkflowStatus.UNAUTHORIZED


def test_approval_requires_validation() -> None:
    c = ApproveContentVersionCommand(idempotency_key="a", request_hash="h", content_version_id=1, digest="d", expected_version=1)
    result = WorkflowDispatcher().dispatch(c, Actor("r", frozenset({Role.REVIEWER})), AuthorizationContext("u", "VALIDATED", processing_state="PROCESSING"))
    assert result.status is WorkflowStatus.VALIDATION_FAILED


def test_publish_requires_vector_sync_and_matching_digest() -> None:
    c = PublishRequestContract(idempotency_key="p", request_hash="h", content_version_id=1, expected_version=1)
    ctx = AuthorizationContext("u", "APPROVED", review_state="APPROVED", vector_sync_state="VECTOR_PENDING", digest="h")
    result = WorkflowDispatcher().dispatch(c, Actor("p", frozenset({Role.PUBLISHER})), ctx)
    assert result.status is WorkflowStatus.VALIDATION_FAILED


def test_executor_failure_is_rejected_and_replay_is_stable() -> None:
    d = WorkflowDispatcher(); actor = Actor("u", frozenset({Role.CREATOR}))
    result = d.dispatch(command(), actor, AuthorizationContext("u", "DRAFT"), lambda _: (_ for _ in ()).throw(ValueError("failed")))
    assert result.status is WorkflowStatus.REJECTED
    assert d.dispatch(command(), actor, AuthorizationContext("u", "DRAFT")) == result


def test_result_serialization_preserves_persian_utf8_zwnj_and_rtl() -> None:
    result = WorkflowDispatcher().dispatch(
        command("می\u200cرود|درس فارسی|\u202bRTL"),
        Actor("u", frozenset({Role.CREATOR})),
        AuthorizationContext("u", "DRAFT"),
    )
    encoded = result.serialize()
    assert "می\u200cرود" in encoded
    assert "درس فارسی" in encoded
    assert "\\u202b" not in encoded
    assert result.serialize() == result.serialize()
