import pytest

from app.services.ai_gateway import (
    AIGateway,
    AIRequest,
    AIResponse,
    MockProvider,
    ProviderError,
    ProviderResponseError,
    redact_secrets,
)


class FailingProvider:
    name = "first"; model = "v1"
    async def health_check(self): return True
    async def generate(self, request): raise ProviderError("TIMEOUT")

class SecondProvider(MockProvider):
    name = "second"; model = "v2"

@pytest.mark.asyncio
async def test_gateway_failover_and_normalized_response():
    response = await AIGateway([FailingProvider(), SecondProvider()]).generate(AIRequest("متن", "SUMMARY"))
    assert response.provider == "second" and response.latency_ms >= 0

@pytest.mark.asyncio
async def test_gateway_does_not_failover_invalid_request():
    with pytest.raises(ProviderError) as exc:
        await AIGateway([MockProvider()]).generate(AIRequest("", "SUMMARY"))
    assert exc.value.code == "INVALID_REQUEST"

def test_secret_redaction():
    assert "supersecret" not in redact_secrets("api_key=supersecret token=abc")

class EmptyProvider:
    name = "empty"; model = "v1"
    async def generate(self, request): return AIResponse(text="", model=self.model)

@pytest.mark.asyncio
async def test_gateway_rejects_empty_provider_response():
    with pytest.raises(ProviderResponseError, match="INVALID_RESPONSE"):
        await AIGateway([EmptyProvider()]).generate(AIRequest("متن", "SUMMARY"))

@pytest.mark.asyncio
async def test_gateway_emits_redacted_success_and_failure_events():
    class Observer:
        def __init__(self): self.events = []
        def emit(self, event): self.events.append(event)
    observer = Observer()
    await AIGateway([FailingProvider(), SecondProvider()], observer=observer).generate(AIRequest("متن", "SUMMARY"))
    assert [event.event_type for event in observer.events] == ["gateway_failure", "gateway_success"]
    assert all(event.prompt_chars == len("متن") for event in observer.events)
