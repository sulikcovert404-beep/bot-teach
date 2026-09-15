import pytest

from app.services.gemini_adapter import GeminiAdapter


@pytest.mark.asyncio
async def test_gemini_adapter_keeps_secret_out_of_public_state():
    adapter = GeminiAdapter(["secret-key"], "test-model")
    assert await adapter.health_check()
    assert not hasattr(adapter, "api_key")
