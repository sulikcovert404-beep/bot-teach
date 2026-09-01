from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class EmbeddingRequest:
    text: str
    task_type: str = "RETRIEVAL_DOCUMENT"
    output_dimensionality: int = 768


class GeminiEmbeddingProvider:
    """Provider-neutral boundary for Gemini text embeddings."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        timeout_seconds: float = 20.0,
    ) -> None:
        if not api_key.strip() or not model.strip() or timeout_seconds <= 0:
            raise ValueError("Gemini embedding configuration is invalid")
        self.api_key = api_key
        self.model = model
        self.timeout = httpx.Timeout(timeout_seconds)

    async def embed(self, request: EmbeddingRequest) -> list[float]:
        if not request.text.strip() or not 128 <= request.output_dimensionality <= 3072:
            raise ValueError("Embedding text and dimensionality are invalid")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:embedContent"
        )
        payload = {
            "content": {"parts": [{"text": request.text}]},
            "taskType": request.task_type,
            "outputDimensionality": request.output_dimensionality,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            data: Any = response.json()
        try:
            values = data["embedding"]["values"]
            vector = [float(value) for value in values]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Gemini returned an invalid embedding response") from exc
        if not vector:
            raise RuntimeError("Gemini returned an empty embedding")
        return vector
