import re
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
        model = request.model or self.default_model
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", model):
            raise ValueError("AI model name is invalid")
        return AIRequest(
            prompt=request.prompt,
            model=model,
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
        if not api_key or timeout_seconds <= 0 or max_retries < 0:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries

    async def generate(self, request: AIRequest) -> AIResponse:
        if not request.prompt.strip() or request.max_tokens < 1:
            raise ValueError("AI request prompt and token limit are invalid")
        model = request.model or "gemini-3.6-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {"maxOutputTokens": request.max_tokens},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(
                        url,
                        headers={"x-goog-api-key": self.api_key},
                        json=payload,
                    )
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
            raise RuntimeError("Gemini returned no text response") from exc
        usage = data.get("usageMetadata", {})
        usage_tokens = usage.get("candidatesTokenCount", usage.get("totalTokenCount"))
        if not isinstance(usage_tokens, int) or usage_tokens < 0:
            usage_tokens = None
        return AIResponse(text=text, model=model, usage_tokens=usage_tokens)
