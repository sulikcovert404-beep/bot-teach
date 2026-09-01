from fastapi.testclient import TestClient

from app.main import app


def test_worksheet_route_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/worksheets",
        json={"title": "تمرین", "instructions": "حل کنید", "questions": [{"prompt": "۱+۱؟"}]},
    )
    assert response.status_code == 401
