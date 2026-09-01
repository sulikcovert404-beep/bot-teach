import pytest

from app.services.ai_gateway import AIRequest, ModelRouter


def test_model_router_applies_default_model_and_cap() -> None:
    routed = ModelRouter("gemini-2.0-flash", max_tokens=1000).route(AIRequest("hello", max_tokens=5000))
    assert routed.model == "gemini-2.0-flash"
    assert routed.max_tokens == 1000


def test_model_router_rejects_invalid_settings() -> None:
    with pytest.raises(ValueError):
        ModelRouter("", max_tokens=1000)


def test_gemini_provider_rejects_negative_retries() -> None:
    from app.services.ai_gateway import GeminiProvider

    with pytest.raises(ValueError):
        GeminiProvider("x" * 32, max_retries=-1)
