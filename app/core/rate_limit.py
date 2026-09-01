import time
from collections import defaultdict

from starlette.types import ASGIApp, Receive, Scope, Send


class InMemoryRateLimitMiddleware:
    """Fixed-window limiter for one process; use a shared store for multiple replicas."""

    def __init__(self, app: ASGIApp, requests: int = 60, window_seconds: int = 60) -> None:
        if requests < 1 or window_seconds < 1:
            raise ValueError("Rate limit settings must be positive")
        self.app = app
        self.requests = requests
        self.window_seconds = window_seconds
        self._windows: defaultdict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = time.monotonic()
        started, count = self._windows[key]
        if now - started >= self.window_seconds:
            started, count = now, 0
        if count >= self.requests:
            await self._reject(send)
            return
        self._windows[key] = (started, count + 1)
        await self.app(scope, receive, send)

    async def _reject(self, send: Send) -> None:
        body = b'{"detail":"Rate limit exceeded"}'
        await send({"type": "http.response.start", "status": 429, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})
