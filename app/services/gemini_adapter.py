"""Gemini adapter for controlled staging use; keys are injected, never logged."""
from __future__ import annotations

import time
from typing import Any

import httpx

from app.services.ai_gateway import AIRequest, AIResponse, ProviderError


class GeminiAdapter:
    name = "gemini"

    def __init__(self, api_keys: list[str], model: str, *, base_url: str = "https://generativelanguage.googleapis.com/v1beta") -> None:
        self._keys = [key.strip() for key in api_keys if key.strip()]
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def health_check(self) -> bool:
        return bool(self._keys)

    async def generate(self, request: AIRequest) -> AIResponse:
        if not self._keys:
            raise ProviderError("PROVIDER_UNAVAILABLE")
        prompt = request.content_context or request.prompt
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": request.parameters or {"maxOutputTokens": request.max_tokens}}
        last: ProviderError | None = None
        for key in self._keys:
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"{self.base_url}/models/{self.model}:generateContent", params={"key": key}, json=payload)
                if response.status_code in (401, 403): raise ProviderError("AUTH_ERROR")
                if response.status_code == 429: raise ProviderError("RATE_LIMIT")
                if response.status_code >= 500: raise ProviderError("SERVER_ERROR")
                if response.status_code >= 400: raise ProviderError("INVALID_REQUEST")
                body: dict[str, Any] = response.json()
                text = body["candidates"][0]["content"]["parts"][0]["text"]
                usage = body.get("usageMetadata", {})
                return AIResponse(
                    text=text,
                    model=self.model,
                    usage_tokens=int(usage.get("candidatesTokenCount", 0)),
                    provider_name=self.name,
                    latency_ms=float(int((time.perf_counter() - started) * 1000)),
                )
            except (httpx.TimeoutException, httpx.NetworkError):
                last = ProviderError("TIMEOUT")
            except (KeyError, TypeError, ValueError):
                last = ProviderError("INVALID_RESPONSE")
            except ProviderError as exc:
                last = exc
            if last and last.code not in {"RATE_LIMIT", "SERVER_ERROR", "TIMEOUT", "PROVIDER_UNAVAILABLE"}:
                raise last
        raise last or ProviderError("PROVIDER_UNAVAILABLE")
