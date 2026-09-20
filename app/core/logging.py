import logging
import re
import time
import uuid
from collections import Counter
from threading import Lock

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("education.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def configure_ai_provider_logging() -> logging.Logger:
    """Enable redacted AI provider events without adding duplicate handlers."""
    provider_logger = logging.getLogger("education.ai_provider")
    provider_logger.setLevel(logging.INFO)
    provider_logger.propagate = True
    if not any(getattr(handler, "_ai_provider_handler", False) for handler in provider_logger.handlers):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._ai_provider_handler = True  # type: ignore[attr-defined]
        provider_logger.addHandler(handler)
    return provider_logger


configure_ai_provider_logging()


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._total = 0
        self._statuses: Counter[str] = Counter()

    def observe(self, status_code: int) -> None:
        with self._lock:
            self._total += 1
            self._statuses[str(status_code)] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {"requests_total": self._total, "responses_by_status": dict(self._statuses)}

    def prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP education_http_requests_total Total HTTP requests observed.",
                "# TYPE education_http_requests_total counter",
                f"education_http_requests_total {self._total}",
                "# HELP education_http_responses_total HTTP responses by status code.",
                "# TYPE education_http_responses_total counter",
            ]
            lines.extend(
                f'education_http_responses_total{{status_code="{status}"}} {count}'
                for status, count in sorted(self._statuses.items())
            )
            return "\n".join(lines) + "\n"


request_metrics = RequestMetrics()


class TelegramMetrics:
    """Low-cardinality Telegram auth/webhook metrics with safe allowlists."""

    AUTH_FAILURES = {"missing_init_data", "invalid_init_data", "expired_session", "provider_error", "db_error", "timeout", "unknown_safe"}
    WEBHOOK_FAILURES = {"missing_secret", "invalid_secret", "invalid_payload", "processing_error", "dependency_error"}
    DEPENDENCIES = {"bot_unavailable", "telegram_timeout", "database_unavailable", "redis_unavailable"}

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[tuple[str, str]] = Counter()
        self._latency: Counter[str] = Counter()

    def _inc(self, name: str, value: str = "") -> None:
        with self._lock:
            self._counters[(name, value)] += 1

    def auth_attempt(self) -> None: self._inc("telegram_auth_attempt_total")
    def auth_success(self) -> None: self._inc("telegram_auth_success_total")
    def auth_failure(self, failure_class: str) -> None: self._inc("telegram_auth_failure_total", failure_class if failure_class in self.AUTH_FAILURES else "unknown_safe")
    def webhook_request(self, status_class: str = "all") -> None: self._inc("telegram_webhook_requests_total", status_class if status_class in {"all", "2xx", "4xx", "5xx"} else "all")
    def webhook_validation_failure(self, failure_class: str) -> None: self._inc("telegram_webhook_validation_failures_total", failure_class if failure_class in self.WEBHOOK_FAILURES else "processing_error")
    def dependency_failure(self, dependency: str) -> None: self._inc("telegram_dependency_failures_total", dependency if dependency in self.DEPENDENCIES else "unknown_safe")
    def observe_latency(self, metric: str, duration_seconds: float) -> None:
        with self._lock:
            self._latency[f"{metric}_count"] += 1
            self._latency[f"{metric}_sum_millis"] += int(duration_seconds * 1000)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {"counters": {f'{k[0]}{{value="{k[1]}"}}': v for k, v in self._counters.items()}, "latency": dict(self._latency)}

    def prometheus(self) -> str:
        with self._lock:
            lines = []
            for (name, value), count in sorted(self._counters.items()):
                label = f'{{value="{value}"}}' if value else ""
                lines.append(f"{name}{label} {count}")
            for name, value in sorted(self._latency.items()):
                lines.append(f"{name} {value}")
            return "\n".join(lines) + ("\n" if lines else "")


telegram_metrics = TelegramMetrics()


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming_headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        candidate = incoming_headers.get("x-request-id", "")
        request_id = candidate if _REQUEST_ID_PATTERN.fullmatch(candidate) else str(uuid.uuid4())
        status_code = 500
        started_at = time.perf_counter()

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode()))
                raw_path = scope.get("path", "")
                is_mini_app = raw_path.startswith(("/mini-app", "/static"))
                sec_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                ]
                if is_mini_app:
                    sec_headers.append(
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'self' 'unsafe-inline' data: https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org; "
                                b"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
                                b"connect-src 'self' https: wss:; img-src 'self' data: https:; "
                                b"frame-ancestors *;"
                            ),
                        )
                    )
                else:
                    sec_headers.extend([
                        (b"x-frame-options", b"DENY"),
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'self'; script-src 'self' https://telegram.org; "
                                b"style-src 'self'; connect-src 'self'; img-src 'self' data:; "
                                b"base-uri 'none'; frame-ancestors 'none'"
                            ),
                        ),
                    ])
                headers.extend(sec_headers)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            request_metrics.observe(status_code)
            duration_seconds = time.perf_counter() - started_at
            if scope.get("path") == "/api/v1/auth/telegram":
                telegram_metrics.observe_latency("telegram_auth_latency_seconds", duration_seconds)
            elif scope.get("path") == "/api/v1/telegram/webhook":
                telegram_metrics.observe_latency("telegram_webhook_processing_latency_seconds", duration_seconds)
            logger.info(
                "request method=%s path=%s status=%s request_id=%s duration_ms=%.2f",
                scope.get("method"),
                scope.get("path"),
                status_code,
                request_id,
                duration_seconds * 1000,
            )
