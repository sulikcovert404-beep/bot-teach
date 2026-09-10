import pytest

from app.services.lesson_pack import LessonPackRequest, SchoolStage
from app.services.lesson_pack_orchestrator import InMemoryAssetStore, LessonPackOrchestrator


@pytest.mark.asyncio
async def test_unapproved_pack_is_denied() -> None:
    request = LessonPackRequest(1, "v1", "نور", "منبع", SchoolStage.ELEMENTARY)
    with pytest.raises(PermissionError, match="UNAPPROVED_ASSET"):
        await LessonPackOrchestrator().delivery_assets(request, review_state="DRAFT")


@pytest.mark.asyncio
async def test_approved_delivery_has_all_static_asset_types() -> None:
    request = LessonPackRequest(2, "v1", "کسر", "منبع", SchoolStage.UPPER_SECONDARY)
    assets = await LessonPackOrchestrator().delivery_assets(request, review_state="APPROVED")
    assert [a.asset_type for a in assets] == ["PODCAST", "PDF", "MCQ", "DESCRIPTIVE"]
    assert all(a.caption.startswith("کسر | UPPER_SECONDARY") for a in assets)


@pytest.mark.asyncio
async def test_persisted_store_reuses_across_orchestrator_instances() -> None:
    store = InMemoryAssetStore()
    request = LessonPackRequest(3, "v1", "آب", "منبع", SchoolStage.LOWER_SECONDARY)
    first = await LessonPackOrchestrator(store=store).generate_or_reuse(request)
    second = await LessonPackOrchestrator(store=store).generate_or_reuse(request)
    assert first is second
    assert await store.get(lesson_id=3, content_version="v1", asset_type="PACK", stage=SchoolStage.LOWER_SECONDARY) is first


@pytest.mark.asyncio
async def test_retry_and_concurrent_requests_are_idempotent() -> None:
    store = InMemoryAssetStore()
    request = LessonPackRequest(4, "v1", "نور", "منبع", SchoolStage.ELEMENTARY)
    orchestrator = LessonPackOrchestrator(store=store)
    results = await __import__("asyncio").gather(
        orchestrator.generate_or_reuse(request),
        orchestrator.generate_or_reuse(request),
        orchestrator.generate_or_reuse(request),
    )
    assert results[0] is results[1] is results[2]
    assert await orchestrator.generate_or_reuse(request) is results[0]


@pytest.mark.asyncio
async def test_content_version_isolation_prevents_old_asset_reuse() -> None:
    store = InMemoryAssetStore()
    orchestrator = LessonPackOrchestrator(store=store)
    old = await orchestrator.generate_or_reuse(LessonPackRequest(5, "v1", "آب", "منبع", SchoolStage.ELEMENTARY))
    new = await orchestrator.generate_or_reuse(LessonPackRequest(5, "v2", "آب", "منبع", SchoolStage.ELEMENTARY))
    assert old is not new
    assert old.content_hash != new.content_hash
