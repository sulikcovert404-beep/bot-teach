import pytest

from app.services.curriculum_pipeline_api import (
    Actor,
    AuthorizationError,
    CASConflictError,
    CommandContext,
    CurriculumPipelineService,
    DigestMismatchError,
    InvalidStateError,
    JobState,
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
    version_id = service.create_content_version(ctx("CONTENT_ADMIN", "c"), 1, "d").result.content_version_id
    service.validate_content(ctx("PIPELINE", "v", 1), version_id)
    service.approve_content(ctx("REVIEWER", "a", 2), version_id, "d")
    with pytest.raises(InvalidStateError):
        service.publish_content_version(ctx("PUBLISHER", "p", 3), version_id)


def test_authorization_and_digest_errors() -> None:
    service = CurriculumPipelineService()
    version_id = service.create_content_version(ctx("CONTENT_ADMIN", "c"), 1, "d").result.content_version_id
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


def test_cas_conflict_and_async_job_contract() -> None:
    service = CurriculumPipelineService()
    version_id = service.create_content_version(ctx("CONTENT_ADMIN", "c"), 1, "d").result.content_version_id
    with pytest.raises(CASConflictError):
        service.validate_content(ctx("PIPELINE", "v", 99), version_id)
    job = service.submit_processing_job(ctx("CONTENT_ADMIN", "job"), version_id)
    assert job.result.status is JobState.ACCEPTED
    assert service.get_job(job.result.job_id).job_id == job.result.job_id

