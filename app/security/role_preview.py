"""Secure, short-lived role-preview context primitives.

Phase A implementation is provider-neutral and intentionally has no route or
persistent state.  A preview token is issued only for a canonical SUPER_ADMIN
and carries an immutable effective role plus server-validated tenant scope.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import uuid4

import jwt

PREVIEW_PURPOSE: Final = "role_preview"
PREVIEW_AUDIENCE: Final = "secure-role-preview"
PREVIEW_ROLES: Final = frozenset({"STUDENT", "TEACHER", "SCHOOL_ADMIN"})
OWNER_ROLE: Final = "SUPER_ADMIN"
DEFAULT_TTL_MINUTES: Final = 10
MAX_TTL_MINUTES: Final = 15


class PreviewAuthorizationError(ValueError):
    """Raised when a preview request is not authorized."""


@dataclass(frozen=True)
class PreviewPrincipal:
    real_identity: str
    real_role: str
    effective_role: str
    preview_tenant: str
    preview_id: str
    purpose: str = PREVIEW_PURPOSE

    @property
    def is_preview(self) -> bool:
        return True


def issue_preview_token(
    *,
    subject: str,
    actor_role: str,
    effective_role: str,
    preview_tenant: str,
    secret: str,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    preview_id: str | None = None,
    now: datetime | None = None,
) -> tuple[str, PreviewPrincipal]:
    """Issue an immutable preview JWT after server-side authorization checks."""
    if not subject.strip() or actor_role != OWNER_ROLE:
        raise PreviewAuthorizationError("Only SUPER_ADMIN may issue previews")
    if effective_role not in PREVIEW_ROLES:
        raise PreviewAuthorizationError("Unsupported preview role")
    if not preview_tenant.strip():
        raise PreviewAuthorizationError("Preview tenant is required")
    if not secret:
        raise PreviewAuthorizationError("Signing secret is required")
    if not 1 <= ttl_minutes <= MAX_TTL_MINUTES:
        raise PreviewAuthorizationError("Preview TTL is outside the allowed range")
    issued = now or datetime.now(UTC)
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=UTC)
    pid = preview_id or uuid4().hex
    expires = issued + timedelta(minutes=ttl_minutes)
    claims = {
        "sub": subject,
        "real_role": OWNER_ROLE,
        "effective_role": effective_role,
        "preview_tenant": preview_tenant,
        "preview_id": pid,
        "purpose": PREVIEW_PURPOSE,
        "iat": issued,
        "exp": expires,
        "aud": PREVIEW_AUDIENCE,
    }
    token = jwt.encode(claims, secret, algorithm="HS256")
    return token, PreviewPrincipal(subject, OWNER_ROLE, effective_role, preview_tenant, pid)


def decode_preview_token(token: str, *, secret: str, now: datetime | None = None) -> PreviewPrincipal:
    """Decode and validate a preview token, failing closed on every claim."""
    if not token or not secret:
        raise PreviewAuthorizationError("Preview token is invalid")
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=PREVIEW_AUDIENCE,
            options={"require": ["sub", "real_role", "effective_role", "preview_tenant", "preview_id", "purpose", "iat", "exp", "aud"]},
        )
    except Exception as exc:
        raise PreviewAuthorizationError("Preview token is invalid or expired") from exc
    if claims.get("real_role") != OWNER_ROLE or claims.get("purpose") != PREVIEW_PURPOSE:
        raise PreviewAuthorizationError("Preview token purpose is invalid")
    subject = claims.get("sub")
    effective = claims.get("effective_role")
    tenant = claims.get("preview_tenant")
    pid = claims.get("preview_id")
    if not all(isinstance(v, str) and v.strip() for v in (subject, effective, tenant, pid)):
        raise PreviewAuthorizationError("Preview claims are incomplete")
    if effective not in PREVIEW_ROLES:
        raise PreviewAuthorizationError("Preview role is invalid")
    return PreviewPrincipal(subject, OWNER_ROLE, effective, tenant, pid)


def ensure_preview_operation_allowed(principal: PreviewPrincipal, operation: str) -> None:
    """Prevent previews from invoking owner-only or preview-issuing operations."""
    forbidden = {"issue_preview", "change_owner", "change_permission", "change_security_policy"}
    if operation in forbidden:
        raise PreviewAuthorizationError("Preview context cannot perform this operation")


def preview_audit_metadata(principal: PreviewPrincipal, *, outcome: str) -> dict[str, object]:
    """Return non-sensitive metadata suitable for AuditLog."""
    return {
        "actor": principal.real_identity,
        "real_role": principal.real_role,
        "effective_role": principal.effective_role,
        "preview_tenant": principal.preview_tenant,
        "preview_id": principal.preview_id,
        "purpose": principal.purpose,
        "outcome": outcome,
    }
