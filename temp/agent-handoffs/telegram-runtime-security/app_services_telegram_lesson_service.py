from __future__ import annotations
from dataclasses import dataclass
from app.services.lesson_pack import LessonPackRequest
from app.services.lesson_pack_orchestrator import LessonPackOrchestrator
from app.services.telegram_delivery import deliver_assets, validate_asset_access, TelegramMediaSender

@dataclass(frozen=True, slots=True)
class TelegramLessonContext:
    chat_id: int
    tenant_id: int
    lesson_id: int
    content_version_id: int
    job_id: int

async def deliver_persisted_lesson_pack(*, bot: TelegramMediaSender, orchestrator: LessonPackOrchestrator, request: LessonPackRequest, context: TelegramLessonContext, review_state: str) -> int:
    validate_asset_access(review_state=review_state, tenant_id=context.tenant_id, requested_tenant_id=context.tenant_id, lesson_id=request.lesson_id, requested_lesson_id=context.lesson_id)
    if request.content_version_id != context.content_version_id:
        raise PermissionError("WRONG_CONTENT_VERSION")
    assets = await orchestrator.delivery_assets_persisted(request, review_state=review_state, job_id=context.job_id)
    await deliver_assets(bot, context.chat_id, assets)
    return len(assets)
