from fastapi.testclient import TestClient

from app.main import app


def test_exam_correction_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/exams/1/correct",
        json={"answer_key": "۱:الف", "answers": "۱:ب"},
    )
    assert response.status_code == 401
