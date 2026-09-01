from fastapi.testclient import TestClient

from app.main import app


def test_mini_app_is_served() -> None:
    response = TestClient(app).get("/mini-app/")
    assert response.status_code == 200
    assert "یارِ یادگیری" in response.text
