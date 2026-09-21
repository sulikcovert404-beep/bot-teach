from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()


def test_teacher_assistant_route_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/teacher/lesson-plan",
        json={"topic": "فتوسنتز", "grade": "هفتم"},
    )
    assert response.status_code == 401
