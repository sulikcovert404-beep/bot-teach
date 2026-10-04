import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimitMiddleware
from app.main import app


def _configured_in_memory_limit() -> int:
    for middleware in app.user_middleware:
        if middleware.cls is InMemoryRateLimitMiddleware:
            return int(middleware.kwargs["requests"])
    pytest.skip("The shared application is configured with a non-memory rate-limit backend")


def test_a_shared_app_enforces_the_configured_in_memory_threshold() -> None:
    requests = _configured_in_memory_limit()
    with TestClient(app) as client:
        for _ in range(requests):
            assert client.get("/health").status_code == 200
        response = client.get("/health")
    assert response.status_code == 429


def test_b_shared_app_starts_with_a_fresh_test_limiter_window() -> None:
    _configured_in_memory_limit()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
