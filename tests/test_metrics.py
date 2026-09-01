from fastapi.testclient import TestClient

from app.main import app


def test_metrics_exposes_request_counters() -> None:
    client = TestClient(app)
    before = client.get("/metrics").json()["requests_total"]
    client.get("/health")
    after = client.get("/metrics").json()
    assert after["requests_total"] >= before + 1
    assert int(after["responses_by_status"]["200"]) >= 1
