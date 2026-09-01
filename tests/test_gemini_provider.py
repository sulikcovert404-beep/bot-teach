from typing import Self

import pytest

from app.services.ai_gateway import AIRequest, GeminiProvider


def test_gemini_provider_requires_key() -> None:
    with pytest.raises(ValueError):
        GeminiProvider("")


def test_gemini_provider_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError):
        GeminiProvider("x" * 32, timeout_seconds=0)


@pytest.mark.asyncio
async def test_gemini_provider_sends_output_token_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **kwargs: object) -> Response:
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    result = await GeminiProvider("x" * 32).generate(
        AIRequest(prompt="Explain photosynthesis", model="gemini-test", max_tokens=321)
    )

    assert result.text == "ok"
    assert captured["json"] == {
        "contents": [{"parts": [{"text": "Explain photosynthesis"}]}],
        "generationConfig": {"maxOutputTokens": 321},
    }
