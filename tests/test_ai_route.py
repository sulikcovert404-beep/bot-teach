from fastapi.testclient import TestClient

from app.main import app


def test_ai_route_requires_authentication() -> None:
    response = TestClient(app).post("/api/v1/ai/generate", json={"prompt": "hello"})
    assert response.status_code == 401


def test_educational_ai_routes_require_authentication() -> None:
    client = TestClient(app)
    summary = client.post("/api/v1/ai/summarize", json={"text": "درس"})
    questions = client.post("/api/v1/ai/questions", json={"text": "درس"})
    exam = client.post("/api/v1/ai/exam", json={"text": "درس"})
    correction = client.post(
        "/api/v1/ai/exam/correct", json={"answer_key": "۱:الف", "answers": "۱:ب"}
    )
    assert summary.status_code == 401
    assert questions.status_code == 401
    assert exam.status_code == 401
    assert correction.status_code == 401


def test_study_plan_route_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/study-plan", json={"tasks": [], "daily_minutes": 30}
    )
    assert response.status_code == 401
