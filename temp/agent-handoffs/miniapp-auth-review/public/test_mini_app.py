from fastapi.testclient import TestClient

from app.main import app


def test_mini_app_is_served() -> None:
    response = TestClient(app).get("/mini-app/")
    assert response.status_code == 200
    assert "یارِ یادگیری" in response.text


def test_mini_app_prevents_duplicate_submissions() -> None:
    response = TestClient(app).get("/mini-app/app.js")
    assert response.status_code == 200
    assert "submitButton.disabled = true" in response.text
    assert "finally" in response.text
