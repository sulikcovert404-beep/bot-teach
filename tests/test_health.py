from typing import Self

import pytest
from fastapi.testclient import TestClient

from app.api.routes import health as health_route
from app.core.config import get_settings
from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_platform_info() -> None:
    response = TestClient(app).get("/api/v1/platform")
    assert response.status_code == 200
    assert response.json()["api_version"] == "v1"


def test_migration_heads_are_resolved_from_source() -> None:
    heads = health_route.migration_heads()
    # The source of truth is the checked-in migration graph, now converged to a single head.
    assert heads == tuple(sorted(heads))
    assert heads == ("20260912_0020",)


def test_readiness_requires_database_configuration() -> None:
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


@pytest.mark.asyncio
async def test_readiness_checks_redis_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        def __init__(self, value: str | int) -> None:
            self.value = value

        def scalar_one_or_none(self) -> str | int:
            return self.value

    class Session:
        async def execute(self, query) -> Result:
            return Result(1 if "SELECT 1" in str(query) else health_route.EXPECTED_MIGRATION_HEAD)

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args) -> None:
            return None

    class Factory:
        def __call__(self) -> Session:
            return Session()

    class Redis:
        @classmethod
        def from_url(cls, _url: str) -> "Redis":
            return cls()

        async def ping(self) -> bool:
            return True

        async def aclose(self) -> None:
            return None

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite://")
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    monkeypatch.setattr(settings, "expected_migration_head", health_route.EXPECTED_MIGRATION_HEAD)
    monkeypatch.setattr(health_route, "build_session_factory", lambda _url: Factory())
    monkeypatch.setattr(health_route, "Redis", Redis)

    assert await health_route.readiness() == {
        "status": "ready",
        "migration_head": health_route.EXPECTED_MIGRATION_HEAD,
    }
