"""Short-lived signed identities for controlled staging acceptance only.

This module never exposes a runtime route and refuses production settings.
"""
from __future__ import annotations

import os

from app.security.tokens import create_access_token


def staging_token(subject: str, role: str, *, expires_minutes: int = 10) -> str:
    """Create a real-contract JWT using only an explicitly non-production secret."""
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"staging", "test", "development"}:
        raise RuntimeError("staging auth fixtures are disabled outside test/staging contexts")
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET must be supplied through the staging environment")
    return create_access_token(subject, secret, expires_minutes=expires_minutes, role=role)
