from fastapi.testclient import TestClient

from app.main import app


def test_admin_billing_routes_require_admin() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/admin/payments").status_code == 401
    assert client.get("/api/v1/admin/subscriptions").status_code == 401
    assert client.put(
        "/api/v1/admin/subscriptions/1", json={"plan": "FREE"}
    ).status_code == 401
    assert client.get("/api/v1/admin/payments?limit=10&offset=20").status_code == 401
    assert client.get("/api/v1/admin/ai-usage/summary").status_code == 401
