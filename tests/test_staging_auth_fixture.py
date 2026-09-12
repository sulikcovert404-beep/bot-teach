import jwt
import pytest

from app.testing.staging_auth import staging_token


def test_staging_token_uses_runtime_claim_contract(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    token = staging_token("42", "STUDENT")
    claims = jwt.decode(token, "x" * 32, algorithms=["HS256"])
    assert claims["sub"] == "42"
    assert claims["role"] == "STUDENT"
    assert "exp" in claims and "iat" in claims


def test_staging_token_fails_closed_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    with pytest.raises(RuntimeError):
        staging_token("42", "STUDENT")
