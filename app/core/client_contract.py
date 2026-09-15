"""Shared client/session contract for Web, Android, and Bale consumers."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID


class AuthChannel(StrEnum):
    TELEGRAM = "telegram"
    BALE = "bale"
    WEB = "web"
    ANDROID = "android"


@dataclass(frozen=True)
class SessionContext:
    user_id: int | UUID
    channel: AuthChannel
    tenant_id: int | UUID | None = None
    access_token: str | None = None
    expires_at: int | None = None


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    status: int
    retryable: bool = False

    @classmethod
    def from_response(cls, status: int, body: Mapping[str, Any] | None) -> "ApiError":
        body = body or {}
        code = body.get("code") if isinstance(body.get("code"), str) else "API_ERROR"
        message = body.get("detail") if isinstance(body.get("detail"), str) else "درخواست ناموفق بود."
        return cls(code=code, message=message, status=status, retryable=status >= 500 or status == 429)
