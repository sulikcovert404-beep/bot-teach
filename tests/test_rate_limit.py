from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimitMiddleware


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
