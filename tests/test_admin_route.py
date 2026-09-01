from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.models import AuditLog
from app.main import app
from app.security.tokens import create_access_token


def test_admin_audit_logs_requires_admin_or_teacher(monkeypatch) -> None:
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    token = create_access_token("1", secret, role="STUDENT")
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_audit_logs_returns_page(monkeypatch) -> None:
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    token = create_access_token("1", secret, role="ADMIN")

    async def override_session():
        class FakeResult:
            def all(self):
                return [
                    AuditLog(
                        id=7,
                        actor_user_id=1,
                        action="create",
                        resource_type="book",
                        resource_id="b-1",
                        metadata_json="{}",
                        created_at=datetime.now(UTC),
                    )
                ]

        class FakeSession:
            async def scalars(self, _query):
                return FakeResult()

        yield FakeSession()

    from app.api.routes.admin import get_session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/audit-logs?limit=10&offset=2",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json()["items"][0]["resource_id"] == "b-1"
        assert response.json()["limit"] == 10
        assert response.json()["offset"] == 2
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_admin_ai_usage_summary_returns_aggregate(monkeypatch) -> None:
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    token = create_access_token("1", secret, role="ADMIN")

    async def override_session():
        class FakeResult:
            def one(self):
                return (3, 900, 720)

        class FakeSession:
            async def execute(self, _query):
                return FakeResult()

        yield FakeSession()

    from app.api.routes.admin import get_session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/ai-usage/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json() == {"event_count": 3, "requested_tokens": 900, "charged_tokens": 720}
    finally:
        app.dependency_overrides.pop(get_session, None)
