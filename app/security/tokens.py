from datetime import UTC, datetime, timedelta

import jwt


def create_access_token(
    subject: str, secret: str, expires_minutes: int = 30, role: str | None = None
) -> str:
    if not secret:
        raise ValueError("JWT secret is required")
    if expires_minutes < 1:
        raise ValueError("Token expiration must be positive")
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> str:
    if not secret:
        raise ValueError("JWT secret is required")
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Token subject is missing")
    return subject


def decode_access_token_claims(token: str, secret: str) -> dict[str, object]:
    if not secret:
        raise ValueError("JWT secret is required")
    return jwt.decode(token, secret, algorithms=["HS256"])
