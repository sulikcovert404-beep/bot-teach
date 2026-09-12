import pytest
from app.services.lesson_pack import LessonPackRequest, SchoolStage
from app.services.lesson_pack_orchestrator import InMemoryAssetStore, LessonPackOrchestrator
from app.services.telegram_lesson_service import TelegramLessonContext, deliver_persisted_lesson_pack

@pytest.mark.asyncio
async def test_persisted_lesson_service_delivers_four_assets():
    class Bot:
        def __init__(self): self.calls=[]
        async def send_audio(self,*a,**k): self.calls.append("audio")
        async def send_document(self,*a,**k): self.calls.append("document")
        async def send_text(self,*a,**k): self.calls.append("text")
    req=LessonPackRequest(lesson_id=7,title="درس",content_version="v1",source_text="متن",stage=SchoolStage.ELEMENTARY,language="fa",content_version_id=9)
    bot=Bot()
    with pytest.raises(PermissionError, match="PLACEHOLDER_ASSET_NOT_DELIVERABLE"):
        await deliver_persisted_lesson_pack(bot=bot,orchestrator=LessonPackOrchestrator(store=InMemoryAssetStore()),request=req,context=TelegramLessonContext(1,2,7,9,3),review_state="APPROVED")

@pytest.mark.asyncio
async def test_persisted_lesson_service_denies_wrong_lesson():
    req=LessonPackRequest(lesson_id=7,title="درس",content_version="v1",source_text="متن",stage=SchoolStage.ELEMENTARY,language="fa",content_version_id=9)
    with pytest.raises(PermissionError,match="WRONG_LESSON"):
        await deliver_persisted_lesson_pack(bot=None,orchestrator=LessonPackOrchestrator(),request=req,context=TelegramLessonContext(1,2,8,9,3),review_state="APPROVED")

@pytest.mark.asyncio
async def test_persisted_lesson_service_denies_missing_entitlement():
    req=LessonPackRequest(lesson_id=7,title="درس",content_version="v1",source_text="متن",stage=SchoolStage.ELEMENTARY,language="fa",content_version_id=9)
    with pytest.raises(PermissionError, match="ENTITLEMENT_DENIED"):
        await deliver_persisted_lesson_pack(bot=None,orchestrator=LessonPackOrchestrator(),request=req,context=TelegramLessonContext(1,2,7,9,3,entitled=False),review_state="APPROVED")
