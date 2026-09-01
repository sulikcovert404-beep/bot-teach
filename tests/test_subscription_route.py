from fastapi.testclient import TestClient

from app.main import app


def test_subscription_route_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/subscription")
    assert response.status_code == 401
