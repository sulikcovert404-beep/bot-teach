from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_platform_info() -> None:
    response = TestClient(app).get("/api/v1/platform")
    assert response.status_code == 200
    assert response.json()["api_version"] == "v1"


def test_readiness_requires_database_configuration() -> None:
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
