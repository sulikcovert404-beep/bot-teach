import pytest

from app.services.lesson_pack import LessonPackRequest, SchoolStage
from app.services.lesson_pack_orchestrator import LessonPackOrchestrator


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
