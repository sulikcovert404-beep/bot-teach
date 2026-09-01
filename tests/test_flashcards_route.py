from fastapi.testclient import TestClient

from app.main import app


def test_flashcard_routes_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/flashcards").status_code == 401
    assert client.post(
        "/api/v1/flashcards", json={"front": "سؤال", "back": "پاسخ"}
    ).status_code == 401
    assert client.post("/api/v1/flashcards/1/review", json={"quality": 5}).status_code == 401
