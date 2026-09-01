import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.security.dependencies import authorize_role, require_roles, require_user
from app.security.tokens import create_access_token


def test_require_user_rejects_missing_credentials() -> None:
    with pytest.raises(HTTPException) as error:
        require_user(None)
    assert error.value.status_code == 401


def test_require_user_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "jwt_secret", "x" * 32)
    token = create_access_token("user-1", "x" * 32)
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert require_user(credentials) == "user-1"


def test_authorize_role_rejects_disallowed_role() -> None:
    with pytest.raises(HTTPException) as error:
        authorize_role("STUDENT", {"TEACHER"})
    assert error.value.status_code == 403


def test_require_roles_checks_role_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "jwt_secret", "x" * 32)
    token = create_access_token("user-1", "x" * 32, role="TEACHER")
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert require_roles("TEACHER")(credentials) == "user-1"
