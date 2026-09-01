from fastapi.testclient import TestClient

from app.main import app


def test_exam_generation_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/exams/generate",
        json={"title": "علوم", "text": "سلول", "count": 5},
    )
    assert response.status_code == 401
