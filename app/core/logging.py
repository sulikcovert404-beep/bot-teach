import logging
import uuid
from collections import Counter
from threading import Lock

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("education.api")


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


request_metrics = RequestMetrics()


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
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
