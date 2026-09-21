"""Focused contract tests for the four dashboard role boundaries.

These tests intentionally exercise the shared production role guard and the
public dashboard shells; they do not require a live database or Telegram.
"""

import secrets

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.security.dependencies import require_roles
from app.security.tokens import create_access_token


@pytest.fixture(autouse=True)
def _ephemeral_jwt_secret(monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated strong JWT secret for this module's auth tests."""
    monkeypatch.setenv("JWT_SECRET", secrets.token_urlsafe(48))
    get_settings.cache_clear()
    try:
        yield
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def credentials(role: str, subject: str = "42") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=create_access_token(subject, get_settings().jwt_secret, role=role),
    )


ROLE_SURFACES = {
    "STUDENT": ("STUDENT",),
    "TEACHER": ("TEACHER",),
    "SCHOOL_ADMIN": ("SCHOOL_ADMIN",),
    "SUPER_ADMIN": ("SUPER_ADMIN",),
}


@pytest.mark.parametrize(("role", "allowed"), ROLE_SURFACES.items())
def test_each_dashboard_role_guard_accepts_only_its_canonical_role(role: str, allowed: tuple[str, ...]) -> None:
    assert require_roles(*allowed)(credentials(role)) == "42"


@pytest.mark.parametrize("target", ROLE_SURFACES)
@pytest.mark.parametrize("role", ("STUDENT", "TEACHER", "SCHOOL_ADMIN", "SUPER_ADMIN"))
def test_wrong_role_is_denied_by_dashboard_guard(target: str, role: str) -> None:
    if role == target:
        pytest.skip("positive case is covered by the acceptance test")
    with pytest.raises(HTTPException) as exc:
        require_roles(target)(credentials(role))
    assert exc.value.status_code == 403


def test_anonymous_dashboard_data_endpoints_fail_closed() -> None:
    client = TestClient(create_app())
    endpoints = (
        "/api/v1/student/v1/assignments",
        "/api/v1/student/progress",
        "/api/v1/teacher/classrooms",
        "/api/v1/admin/users",
    )
    for endpoint in endpoints:
        assert client.get(endpoint).status_code == 401
