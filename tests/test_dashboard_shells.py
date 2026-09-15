from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_shells_and_assets_are_served() -> None:
    client = TestClient(app)
    surfaces = (
        "/teacher-dashboard/",
        "/student-dashboard/",
        "/platform/",
    )
    for surface in surfaces:
        page = client.get(surface)
        assert page.status_code == 200
        assert 'dir="rtl"' in page.text
        assert "<script" in page.text

    assert 'id="contentBtn"' in client.get("/student-dashboard/").text

    platform_page = client.get("/platform/")
    assert "Mock API" not in platform_page.text
    assert "telegram-web-app.js" in platform_page.text
    assert client.get("/platform/ui/auth-bootstrap.js").status_code == 200


def test_dashboard_scripts_are_available() -> None:
    client = TestClient(app)
    for surface in ("teacher-dashboard", "student-dashboard", "platform"):
        assert client.get(f"/{surface}/app.js").status_code == 200


def test_dashboard_data_endpoints_fail_closed_without_session() -> None:
    client = TestClient(app)
    for endpoint in ("/api/v1/admin/users", "/api/v1/teacher/classrooms", "/api/v1/student/v1/assignments", "/api/v1/student/progress"):
        assert client.get(endpoint).status_code == 401


