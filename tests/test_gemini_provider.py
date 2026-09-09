from typing import Self

import pytest

from app.services.ai_gateway import (
    AIRequest,
    AIProviderEvent,
    GeminiProvider,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderResponseError,
    ProviderTransientError,
    StructuredLoggingAIProviderObserver,
)


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
            return {
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
                "usageMetadata": {"totalTokenCount": 42, "candidatesTokenCount": 17},
            }

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
    assert result.usage_tokens == 17
    assert captured["headers"] == {"x-goog-api-key": "x" * 32}
    assert captured["json"] == {
        "contents": [{"parts": [{"text": "Explain photosynthesis"}]}],
        "generationConfig": {"maxOutputTokens": 321},
    }


@pytest.mark.asyncio
async def test_gemini_provider_uses_current_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
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

        async def post(self, url: str, **kwargs: object) -> Response:
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    result = await GeminiProvider("x" * 32).generate(AIRequest(prompt="hello", max_tokens=64))

    assert result.text == "ok"
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.6-flash:generateContent"
    )


@pytest.mark.asyncio
async def test_gemini_provider_reports_textless_success_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}]}

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> object:
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(ProviderResponseError, match="no text response"):
        await GeminiProvider("x" * 32).generate(AIRequest(prompt="hello", max_tokens=64))


class EventObserver:
    def __init__(self, fail: bool = False) -> None:
        self.events: list[AIProviderEvent] = []
        self.fail = fail

    def emit(self, event: AIProviderEvent) -> None:
        if self.fail:
            raise RuntimeError("observer unavailable")
        self.events.append(event)


def test_structured_logging_observer_emits_redacted_event(caplog: pytest.LogCaptureFixture) -> None:
    observer = StructuredLoggingAIProviderObserver()
    event = AIProviderEvent(
        "ai_request_failed",
        "gemini",
        "gemini-test",
        "ai_tutor",
        "failed",
        12.5,
        "ProviderQuotaError",
        12.0,
    )
    with caplog.at_level("INFO", logger="education.ai_provider"):
        observer.emit(event)
    assert "ai_provider_event=" in caplog.text
    assert "ProviderQuotaError" in caplog.text
    for forbidden in ("private prompt", "answer text", "api-key", "telegram token", "authorization"):
        assert forbidden not in caplog.text.casefold()


@pytest.mark.asyncio
async def test_provider_emits_success_event_without_sensitive_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 200
        headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "candidates": [{"content": {"parts": [{"text": "answer"}]}}],
                "usageMetadata": {"candidatesTokenCount": 7},
            }

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    observer = EventObserver()
    await GeminiProvider("secret-key", observer=observer).generate(
        AIRequest(prompt="private prompt", model="gemini-test", task_type="ai_tutor")
    )
    assert [event.event_type for event in observer.events] == [
        "ai_request_started",
        "ai_request_completed",
    ]
    event = observer.events[-1]
    assert event.provider == "gemini"
    assert event.model == "gemini-test"
    assert event.task_type == "ai_tutor"
    assert event.status == "completed"
    assert event.final_outcome == "success"
    assert event.error_category is None
    assert event.attempts == 1
    assert event.retry_count == 0
    assert event.fallback_attempts == 0
    assert event.latency_ms is not None and event.latency_ms >= 0
    assert event.prompt_chars == len("private prompt")
    assert event.context_chars is None
    assert event.requested_tokens == 1000
    assert event.usage_tokens == 7
    assert "private prompt" not in event.serialize()
    assert "answer" not in event.serialize()
    assert "secret-key" not in event.serialize()
    assert '"requested_tokens":1000' in event.serialize()
    assert '"usage_tokens":7' in event.serialize()


@pytest.mark.asyncio
async def test_provider_emits_quota_event_with_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 429
        headers = {"retry-after": "12"}

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    observer = EventObserver()
    with pytest.raises(ProviderQuotaError):
        await GeminiProvider("x" * 32, observer=observer).generate(AIRequest(prompt="hello"))
    event = observer.events[-1]
    assert event.event_type == "ai_request_failed"
    assert event.error_type == "ProviderQuotaError"
    assert event.retry_after == 12
    assert event.final_outcome == "quota_exhausted"
    assert event.error_category == "quota_exhausted"
    assert event.attempts == 1
    assert event.retry_count == 0
    assert event.fallback_attempts == 0
    assert event.latency_ms is not None and event.latency_ms >= 0
    assert event.prompt_chars == len("hello")
    assert event.context_chars is None
    assert event.requested_tokens == 1000
    assert event.usage_tokens is None
    assert "hello" not in event.serialize()


@pytest.mark.asyncio
async def test_provider_emits_auth_and_transient_events(monkeypatch: pytest.MonkeyPatch) -> None:
    class AuthResponse:
        status_code = 401
        headers: dict[str, str] = {}

    class AuthClient:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> AuthResponse:
            return AuthResponse()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: AuthClient())
    observer = EventObserver()
    with pytest.raises(ProviderAuthError):
        await GeminiProvider("x" * 32, observer=observer).generate(AIRequest(prompt="hello"))
    assert observer.events[-1].error_type == "ProviderAuthError"

    class TimeoutClient(AuthClient):
        async def post(self, *_args: object, **_kwargs: object) -> object:
            raise __import__("httpx").TimeoutException("timeout")

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: TimeoutClient())
    observer = EventObserver()
    with pytest.raises(ProviderTransientError):
        await GeminiProvider("x" * 32, max_retries=0, observer=observer).generate(
            AIRequest(prompt="hello")
        )
    assert observer.events[-1].error_type == "ProviderTransientError"


@pytest.mark.asyncio
async def test_observer_failure_does_not_change_provider_result(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 200
        headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    result = await GeminiProvider("x" * 32, observer=EventObserver(fail=True)).generate(
        AIRequest(prompt="hello")
    )
    assert result.text == "ok"


@pytest.mark.asyncio
async def test_gemini_provider_classifies_quota_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 429
        headers = {"retry-after": "12"}

        def raise_for_status(self) -> None:
            raise AssertionError("quota responses must not be retried")

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(ProviderQuotaError) as exc_info:
        await GeminiProvider("x" * 32).generate(AIRequest(prompt="hello"))
    assert exc_info.value.retry_after == 12


@pytest.mark.asyncio
async def test_gemini_provider_does_not_retry_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 403
        headers: dict[str, str] = {}

    class Client:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(ProviderAuthError):
        await GeminiProvider("x" * 32).generate(AIRequest(prompt="hello"))
