import time
from collections import defaultdict

from redis.exceptions import RedisError
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
        self._prune(now)
        started, count = self._windows[key]
        if now - started >= self.window_seconds:
            started, count = now, 0
        if count >= self.requests:
            retry_after = max(1, int(self.window_seconds - (now - started)))
            await self._reject(send, retry_after)
            return
        self._windows[key] = (started, count + 1)
        await self.app(scope, receive, send)

    def _prune(self, now: float) -> None:
        expired = [
            key for key, (started, _count) in self._windows.items()
            if now - started >= self.window_seconds
        ]
        for key in expired:
            del self._windows[key]

    async def _reject(self, send: Send, retry_after: int) -> None:
        body = b'{"detail":"Rate limit exceeded"}'
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(retry_after).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class RedisRateLimitMiddleware(InMemoryRateLimitMiddleware):
    """Shared fixed-window limiter with an in-memory fallback for local development."""

    def __init__(self, app: ASGIApp, redis_url: str, requests: int = 60, window_seconds: int = 60) -> None:
        super().__init__(app, requests, window_seconds)
        from redis.asyncio import Redis

        self._redis = Redis.from_url(redis_url, decode_responses=True)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = f"rate-limit:{client[0] if client else 'unknown'}"
        try:
            count = int(await self._redis.incr(key))
            if count == 1:
                await self._redis.expire(key, self.window_seconds)
            if count > self.requests:
                ttl = int(await self._redis.ttl(key))
                await self._reject(send, max(1, ttl))
                return
        except (RedisError, OSError, TimeoutError):
            # Redis outages must not take the API down; local limiting remains active.
            await super().__call__(scope, receive, send)
            return
        await self.app(scope, receive, send)
