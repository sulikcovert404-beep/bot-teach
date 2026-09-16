import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.security.dependencies import require_roles
from app.security.tokens import create_access_token


def _credentials(token: str):
    from fastapi.security import HTTPAuthorizationCredentials

    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_route_auth_rejects_missing_credentials() -> None:
    with pytest.raises(HTTPException) as exc:
        require_roles("TEACHER") (None)
    assert exc.value.status_code == 401


def test_route_auth_rejects_wrong_role(monkeypatch) -> None:
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    token = create_access_token("101", secret, role="STUDENT")
    with pytest.raises(HTTPException) as exc:
        require_roles("TEACHER")(_credentials(token))
    assert exc.value.status_code == 403


def test_route_auth_accepts_expected_role_and_preserves_identity(monkeypatch) -> None:
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    token = create_access_token("101", secret, role="TEACHER")
    assert require_roles("TEACHER")(_credentials(token)) == "101"


@pytest.mark.parametrize("path", ["/api/v1/teacher/classrooms", "/api/v1/student/v1/assignments"])
def test_real_protected_routes_reject_anonymous_requests(path: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 401


def test_real_teacher_route_rejects_student_token(monkeypatch) -> None:
    secret = "x" * 32
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    token = create_access_token("102", secret, role="STUDENT")
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/teacher/classrooms",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
