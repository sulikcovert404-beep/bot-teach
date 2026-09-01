from fastapi.testclient import TestClient

from app.main import app


def test_analytics_summary_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/analytics/summary")
    assert response.status_code == 401
