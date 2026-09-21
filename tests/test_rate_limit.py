from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimitMiddleware, RedisRateLimitMiddleware
from app.main import create_app


def test_rate_limit_returns_429_after_window_quota() -> None:
    app = FastAPI()
    app.add_middleware(InMemoryRateLimitMiddleware, requests=1, window_seconds=60)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/").status_code == 200
    response = client.get("/")
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1


def test_redis_rate_limit_uses_shared_counter(monkeypatch) -> None:
    class FakeRedis:
        count = 0

        @classmethod
        def from_url(cls, _url: str, **_kwargs: object) -> "FakeRedis":
            return cls()

        async def incr(self, _key: str) -> int:
            FakeRedis.count += 1
            return FakeRedis.count

        async def expire(self, _key: str, _seconds: int) -> bool:
            return True

        async def ttl(self, _key: str) -> int:
            return 42

    monkeypatch.setattr("redis.asyncio.Redis.from_url", FakeRedis.from_url)
    app = FastAPI()
    app.add_middleware(
        RedisRateLimitMiddleware,
        redis_url="redis://test",
        requests=1,
        window_seconds=60,
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/").status_code == 200
    response = client.get("/")
    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"


def test_create_app_isolates_rate_limit_state_without_reset() -> None:
    app_a = create_app()
    with TestClient(app_a) as client_a:
        responses = [client_a.get("/health") for _ in range(61)]
    assert all(response.status_code == 200 for response in responses[:60])
    assert responses[60].status_code == 429

    app_b = create_app()
    with TestClient(app_b) as client_b:
        first = client_b.get("/health")
    assert first.status_code == 200
