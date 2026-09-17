import pytest

from app.services.lesson_pack_orchestrator import DeliveryAsset
from app.services.telegram_delivery import deliver_assets


@pytest.mark.asyncio
async def test_deliver_assets_dispatches_media_without_generation():
    class Bot:
        def __init__(self): self.calls=[]
        async def send_audio(self,*a,**k): self.calls.append(("audio",a,k))
        async def send_document(self,*a,**k): self.calls.append(("document",a,k))
        async def send_text(self,*a,**k): self.calls.append(("text",a,k))
    bot=Bot()
    await deliver_assets(bot, 7, (DeliveryAsset("PODCAST","a","c"),DeliveryAsset("PDF","d","c"),DeliveryAsset("MCQ","q","c"),DeliveryAsset("DESCRIPTIVE","x","c")))
    assert [c[0] for c in bot.calls] == ["audio","document","text","text"]

@pytest.mark.asyncio
async def test_deliver_assets_rejects_missing():
    with pytest.raises(ValueError, match="MISSING_ASSET"):
        await deliver_assets(type("B",(),{})(), 1, (DeliveryAsset("PDF","","c"),))

@pytest.mark.asyncio
async def test_deliver_assets_blocks_placeholder_by_default():
    asset = DeliveryAsset("PDF", "placeholder", "c", is_placeholder=True)
    with pytest.raises(PermissionError, match="PLACEHOLDER_ASSET_NOT_DELIVERABLE"):
        await deliver_assets(type("B", (), {})(), 1, (asset,))

@pytest.mark.asyncio
async def test_deliver_assets_can_explicitly_allow_placeholder_in_controlled_env():
    class Bot:
        async def send_document(self, *args, **kwargs): pass
    await deliver_assets(Bot(), 1, (DeliveryAsset("PDF", "placeholder", "c", True),), allow_placeholders=True)
