from fastapi.testclient import TestClient

from app.main import app


def test_admin_dashboard_shell_is_served() -> None:
    response = TestClient(app).get("/admin-dashboard/")
    assert response.status_code == 200
    assert "مرکز کنترل" in response.text
    assert 'dir="rtl"' in response.text
    assert 'data-view="usage"' in response.text
    assert 'data-view="subscriptions"' in response.text
    assert 'data-view="payments"' in response.text


def test_admin_dashboard_assets_are_served() -> None:
    client = TestClient(app)
    assert client.get("/admin-dashboard/app.js").status_code == 200
    assert client.get("/admin-dashboard/styles.css").status_code == 200
