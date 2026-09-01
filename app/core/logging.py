import logging
import re
import uuid
from collections import Counter
from threading import Lock

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("education.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


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

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self' https://telegram.org; "
                            b"style-src 'self'; connect-src 'self'; img-src 'self' data:; "
                            b"base-uri 'none'; frame-ancestors 'none'",
                        ),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_status)
        request_metrics.observe(status_code)
        logger.info(
            "request method=%s path=%s status=%s request_id=%s",
            scope.get("method"),
            scope.get("path"),
            status_code,
            request_id,
        )
