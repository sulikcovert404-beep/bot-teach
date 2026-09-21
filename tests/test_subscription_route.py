from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()


def test_subscription_route_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/subscription")
    assert response.status_code == 401
