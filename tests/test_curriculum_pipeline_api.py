import pytest

from app.services.curriculum_pipeline_api import (
    Actor,
    AuthorizationError,
    CASConflictError,
    CommandContext,
    CurriculumPipelineService,
    DigestMismatchError,
    IdempotencyConflictError,
    InvalidStateError,
    JobState,
    VectorSyncState,
)


def ctx(role: str, key: str, version: int | None = None) -> CommandContext:
    return CommandContext(Actor(7, role, "tenant-1"), key, version)


def prepared() -> tuple[CurriculumPipelineService, int]:
    service = CurriculumPipelineService()
    created = service.create_content_version(ctx("CONTENT_ADMIN", "create"), 10, "digest-1")
    version_id = created.result.content_version_id
    service.validate_content(ctx("PIPELINE", "validate", 1), version_id)
    service.approve_content(ctx("REVIEWER", "approve", 2), version_id, "digest-1")
    service.mark_vector_synced(ctx("PIPELINE", "sync", 3), version_id, "digest-1")
    return service, version_id


def test_staged_flow_and_publish_gate() -> None:
    service, version_id = prepared()
    receipt = service.publish_content_version(ctx("PUBLISHER", "publish", 4), version_id)
    assert receipt.status == "COMMITTED"


def test_publish_cannot_trigger_vector_sync() -> None:
    service = CurriculumPipelineService()
    version_id = service.create_content_version(
        ctx("CONTENT_ADMIN", "c"), 1, "d"
    ).result.content_version_id
    service.validate_content(ctx("PIPELINE", "v", 1), version_id)
    service.approve_content(ctx("REVIEWER", "a", 2), version_id, "d")
    with pytest.raises(InvalidStateError):
        service.publish_content_version(ctx("PUBLISHER", "p", 3), version_id)


def test_authorization_and_digest_errors() -> None:
    service = CurriculumPipelineService()
    version_id = service.create_content_version(
        ctx("CONTENT_ADMIN", "c"), 1, "d"
    ).result.content_version_id
    with pytest.raises(AuthorizationError):
        service.validate_content(ctx("REVIEWER", "v", 1), version_id)
    with pytest.raises(DigestMismatchError):
        service.approve_content(ctx("REVIEWER", "a", 1), version_id, "wrong")


def test_idempotency_returns_original_receipt() -> None:
    service = CurriculumPipelineService()
    first = service.create_content_version(ctx("CONTENT_ADMIN", "same"), 1, "d")
    second = service.create_content_version(ctx("CONTENT_ADMIN", "same"), 1, "d")
    assert second.command_id == first.command_id
    assert second.result.content_version_id == first.result.content_version_id


def test_idempotency_key_reuse_with_different_request_is_rejected() -> None:
    service = CurriculumPipelineService()
    first = service.create_content_version(
        CommandContext(Actor(7, "CONTENT_ADMIN"), "same", request_hash="h1"), 1, "d"
    )
    assert first.status == "COMMITTED"
    with pytest.raises(IdempotencyConflictError, match="different request"):
        service.create_content_version(
            CommandContext(Actor(7, "CONTENT_ADMIN"), "same", request_hash="h2"), 2, "d2"
        )


def test_publish_requires_digest_bound_approval() -> None:
    service, version_id = prepared()
    snapshot = service.get_content_status(version_id)
    assert snapshot.vector_sync_state is VectorSyncState.SYNCED
    assert snapshot.approval_digest == snapshot.digest


def test_idempotency_conflict_does_not_mutate_state() -> None:
    service = CurriculumPipelineService()
    created = service.create_content_version(
        CommandContext(Actor(7, "CONTENT_ADMIN"), "create", request_hash="h1"), 1, "d"
    )
    version_id = created.result.content_version_id
    before = service.get_content_status(version_id)
    with pytest.raises(IdempotencyConflictError):
        service.validate_content(
            CommandContext(Actor(7, "PIPELINE"), "create", 1, request_hash="h2"),
            version_id,
        )
    assert service.get_content_status(version_id) == before


def test_cas_conflict_and_async_job_contract() -> None:
    service = CurriculumPipelineService()
    version_id = service.create_content_version(
        ctx("CONTENT_ADMIN", "c"), 1, "d"
    ).result.content_version_id
    with pytest.raises(CASConflictError):
        service.validate_content(ctx("PIPELINE", "v", 99), version_id)
    job = service.submit_processing_job(ctx("CONTENT_ADMIN", "job"), version_id)
    assert job.result.status is JobState.ACCEPTED
    assert service.get_job(job.result.job_id).job_id == job.result.job_id
