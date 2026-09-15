import pytest

from app.adapters.bale import BaleAdapter


@pytest.mark.asyncio
async def test_bale_adapter_builds_canonical_command():
    adapter = BaleAdapter()
    context = await adapter.authenticate({"sender_id": "u-1", "trace_id": "t-1"})
    command = await adapter.to_command({"update_id": 7, "text": "سلام"}, context)
    assert command.name == "bale.message"
    assert command.context.channel.value == "bale"
    assert command.idempotency_key == "7"

@pytest.mark.asyncio
async def test_bale_transport_is_explicitly_unconnected():
    with pytest.raises(RuntimeError, match="not connected"):
        await BaleAdapter().send_message("u-1", "سلام")
