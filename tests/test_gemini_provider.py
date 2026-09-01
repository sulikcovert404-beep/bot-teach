import pytest

from app.services.ai_gateway import GeminiProvider


def test_gemini_provider_requires_key() -> None:
    with pytest.raises(ValueError):
        GeminiProvider("")

