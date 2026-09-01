from typing import Self

import pytest

from app.services.embeddings import EmbeddingRequest, GeminiEmbeddingProvider


def test_embedding_provider_rejects_invalid_request() -> None:
    with pytest.raises(ValueError):
        GeminiEmbeddingProvider("")


@pytest.mark.asyncio
async def test_gemini_embedding_provider_sends_secure_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"embedding": {"values": [0.1, 0.2, 0.3]}}

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    result = await GeminiEmbeddingProvider("x" * 32).embed(
        EmbeddingRequest("فتوسنتز چیست؟", output_dimensionality=768)
    )

    assert result == [0.1, 0.2, 0.3]
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-embedding-001:embedContent"
    )
    assert captured["headers"] == {"x-goog-api-key": "x" * 32}


@pytest.mark.asyncio
async def test_gemini_embedding_provider_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        await GeminiEmbeddingProvider("x" * 32).embed(EmbeddingRequest(""))
