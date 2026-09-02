import pytest
from fastapi.testclient import TestClient

from app.api.routes.sources import IngestRequest
from app.main import app


def test_source_ingestion_requires_staff_role() -> None:
    response = TestClient(app).post(
        "/api/v1/sources",
        json={"source_id": "s1", "title": "کتاب", "text": "متن"},
    )
    assert response.status_code == 401


def test_source_search_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/sources/search?query=سلول&limit=5")
    assert response.status_code == 401


def test_source_uri_rejects_unsafe_schemes_and_credentials() -> None:
    with pytest.raises(ValueError):
        IngestRequest(source_id="s1", title="کتاب", text="متن", uri="file:///etc/passwd")
    with pytest.raises(ValueError):
        IngestRequest(source_id="s1", title="کتاب", text="متن", uri="https://user:pass@example.test/book")
