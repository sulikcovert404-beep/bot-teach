from fastapi.testclient import TestClient

from app.main import app


def test_metrics_exposes_request_counters() -> None:
    client = TestClient(app)
    before = client.get("/metrics").json()["requests_total"]
    client.get("/health")
    after = client.get("/metrics").json()
    assert after["requests_total"] >= before + 1
    assert int(after["responses_by_status"]["200"]) >= 1


def test_request_id_is_propagated_when_valid() -> None:
    response = TestClient(app).get("/health", headers={"X-Request-ID": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"


def test_request_id_is_replaced_when_invalid() -> None:
    response = TestClient(app).get("/health", headers={"X-Request-ID": "bad value"})
    request_id = response.headers["x-request-id"]
    assert request_id != "bad value"
    assert len(request_id) == 36


def test_prometheus_metrics_contract() -> None:
    response = TestClient(app).get("/metrics/prometheus")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert "education_http_requests_total" in response.text
    assert "education_http_responses_total" in response.text
