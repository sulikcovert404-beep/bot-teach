import re
import asyncio
from dataclasses import dataclass
import json
import logging
import time
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


@dataclass(frozen=True)
class AIProviderEvent:
    event_type: str
    provider: str
    model: str
    task_type: str
    status: str
    duration_ms: float
    error_type: str | None = None
    retry_after: float | None = None
    fallback_used: bool = False
    trace_id: str | None = None
    user_id: int | None = None
    # Phase 0 observability fields. These contain metadata only; never prompt,
    # response content, credentials, tokens, or chat identifiers.
    final_outcome: str | None = None
    error_category: str | None = None
    attempts: int = 0
    retry_count: int = 0
    fallback_attempts: int = 0
    latency_ms: float | None = None

    def serialize(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))


class AIProviderObserver(Protocol):
    def emit(self, event: AIProviderEvent) -> None: ...


class NoopAIProviderObserver:
    def emit(self, event: AIProviderEvent) -> None:
        return None


class StructuredLoggingAIProviderObserver:
    """Emit only the redacted provider event through application logging."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("education.ai_provider")

    def emit(self, event: AIProviderEvent) -> None:
        self._logger.info("ai_provider_event=%s", event.serialize())


class ProviderError(RuntimeError):
    """Base class for errors that are safe to map at the API boundary."""


class ProviderQuotaError(ProviderError):
    def __init__(self, message: str = "AI provider quota exhausted", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ProviderTransientError(ProviderError):
    pass


class ProviderAuthError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


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

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        observer: AIProviderObserver | None = None,
    ) -> None:
        if not api_key or timeout_seconds <= 0 or max_retries < 0:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries
        self.observer = observer or NoopAIProviderObserver()

    async def generate(self, request: AIRequest) -> AIResponse:
        if not request.prompt.strip() or request.max_tokens < 1:
            raise ValueError("AI request prompt and token limit are invalid")
        models = [request.model or "gemini-3.6-flash"]
        started = time.perf_counter()
        model = models[0]
        self._emit(AIProviderEvent(
            "ai_request_started", "gemini", model, request.task_type, "started", 0.0,
        ))
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {"maxOutputTokens": request.max_tokens},
        }
        data: dict[str, object] | None = None
        used_model = models[0]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{used_model}:generateContent"
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(url, headers={"x-goog-api-key": self.api_key}, json=payload)
                    status_code = getattr(response, "status_code", 200)
                    if status_code == 429:
                        retry_after = _retry_after_seconds(response)
                        error = ProviderQuotaError(retry_after=retry_after)
                        self._emit_failure(request, model, started, error, attempt)
                        raise error
                    if status_code in (401, 403):
                        error = ProviderAuthError("Gemini authentication failed")
                        self._emit_failure(request, model, started, error, attempt)
                        raise error
                    if status_code in (400, 404):
                        error = ProviderResponseError("Gemini rejected the request")
                        self._emit_failure(request, model, started, error, attempt)
                        raise error
                    if status_code >= 500:
                        if attempt == self.max_retries:
                            error = ProviderTransientError("Gemini server error after retries")
                            self._emit_failure(request, model, started, error, attempt)
                            raise error
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    data = response.json()
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt == self.max_retries:
                        error = ProviderTransientError("Gemini request failed after retries")
                        self._emit_failure(request, model, started, error, attempt)
                        raise error from exc
                    await asyncio.sleep(0.5 * (attempt + 1))
            if data is None:
                error = ProviderTransientError("Gemini request returned no response")
                self._emit_failure(request, model, started, error, self.max_retries)
                raise error
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            error = ProviderResponseError("Gemini returned no text response")
            self._emit_failure(request, model, started, error, self.max_retries)
            raise error from exc
        usage = data.get("usageMetadata", {})
        usage_tokens = usage.get("candidatesTokenCount", usage.get("totalTokenCount"))
        if not isinstance(usage_tokens, int) or usage_tokens < 0:
            usage_tokens = None
        result = AIResponse(text=text, model=used_model, usage_tokens=usage_tokens)
        self._emit(AIProviderEvent(
            "ai_request_completed", "gemini", used_model, request.task_type, "completed",
            self._duration_ms(started),
            final_outcome="success",
            attempts=attempt + 1,
            retry_count=attempt,
            latency_ms=self._duration_ms(started),
        ))
        return result

    @staticmethod
    def _duration_ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 3)

    def _emit(self, event: AIProviderEvent) -> None:
        try:
            self.observer.emit(event)
        except Exception:
            pass

    def _emit_failure(
        self,
        request: AIRequest,
        model: str,
        started: float,
        error: ProviderError,
        attempt: int,
    ) -> None:
        self._emit(AIProviderEvent(
            "ai_request_failed",
            "gemini",
            model,
            request.task_type,
            "failed",
            self._duration_ms(started),
            type(error).__name__,
            getattr(error, "retry_after", None),
            final_outcome=_error_category(error),
            error_category=_error_category(error),
            attempts=attempt + 1,
            retry_count=attempt,
            latency_ms=self._duration_ms(started),
        ))


def _error_category(error: ProviderError) -> str:
    if isinstance(error, ProviderQuotaError):
        return "quota_exhausted"
    if isinstance(error, ProviderAuthError):
        return "auth_error"
    if isinstance(error, ProviderTransientError):
        return "timeout" if "request failed" in str(error).casefold() else "provider_error"
    return "provider_error"


def _retry_after_seconds(response: object) -> float | None:
    headers = getattr(response, "headers", {})
    value = headers.get("retry-after") if hasattr(headers, "get") else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
