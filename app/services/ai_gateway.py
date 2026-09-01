from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    model: str | None = None
    max_tokens: int = 1000
    task_type: str = "general"


@dataclass(frozen=True)
class AIResponse:
    text: str
    model: str
    usage_tokens: int | None = None


@dataclass(frozen=True)
class UsageRecord:
    task_type: str
    model: str
    requested_tokens: int
    charged_tokens: int


class AIProvider(Protocol):
    async def generate(self, request: AIRequest) -> AIResponse: ...


class ModelRouter:
    def __init__(self, default_model: str, max_tokens: int = 4000) -> None:
        if not default_model or max_tokens < 1:
            raise ValueError("AI router settings are invalid")
        self.default_model = default_model
        self.max_tokens = max_tokens

    def route(self, request: AIRequest) -> AIRequest:
        return AIRequest(
            prompt=request.prompt,
            model=request.model or self.default_model,
            max_tokens=min(request.max_tokens, self.max_tokens),
            task_type=request.task_type,
        )


class AIRouter:
    """Provider-neutral boundary; concrete providers are injected by composition root."""

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def generate(self, request: AIRequest) -> AIResponse:
        return await self._provider.generate(request)


class GeminiProvider:
    """Minimal provider adapter; credentials never enter request logs or error messages."""

    def __init__(self, api_key: str, timeout_seconds: float = 20.0, max_retries: int = 2) -> None:
        if not api_key or max_retries < 0:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries

    async def generate(self, request: AIRequest) -> AIResponse:
        model = request.model or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {"contents": [{"parts": [{"text": request.prompt}]}]}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(url, params={"key": self.api_key}, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    break
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
                    if attempt == self.max_retries:
                        raise RuntimeError("Gemini request failed after retries") from None
            else:
                raise RuntimeError("Gemini request failed")
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Gemini returned an invalid response") from exc
        return AIResponse(text=text, model=model, usage_tokens=None)
