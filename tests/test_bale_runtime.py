import pytest

from app.adapters.bale import BaleAdapter
from app.core.channels import ChannelResponse


@pytest.mark.asyncio
async def test_bale_runtime_event_reaches_core_handler():
    seen = []
    async def handler(command):
        seen.append(command)
        return ChannelResponse(body={"ok": True})
    response = await BaleAdapter(command_handler=handler).handle_event({"sender_id": "b-1", "update_id": 9, "text": "سلام"})
    assert response.body == {"ok": True}
    assert seen[0].context.channel.value == "bale"
    assert seen[0].idempotency_key == "9"
