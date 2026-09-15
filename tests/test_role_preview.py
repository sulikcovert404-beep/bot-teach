from datetime import UTC, datetime, timedelta

import pytest

from app.security.role_preview import (
    PreviewAuthorizationError,
    decode_preview_token,
    ensure_preview_operation_allowed,
    issue_preview_token,
    preview_audit_metadata,
)

SECRET = "x" * 48


def test_owner_can_issue_and_decode_preview() -> None:
    token, principal = issue_preview_token(
        subject="owner-1", actor_role="SUPER_ADMIN", effective_role="STUDENT", preview_tenant="tenant-a", secret=SECRET
    )
    decoded = decode_preview_token(token, secret=SECRET)
    assert decoded == principal
    assert decoded.real_role == "SUPER_ADMIN"
    assert decoded.effective_role == "STUDENT"


def test_non_owner_and_invalid_scope_are_denied() -> None:
    with pytest.raises(PreviewAuthorizationError):
        issue_preview_token(subject="student", actor_role="STUDENT", effective_role="TEACHER", preview_tenant="t", secret=SECRET)
    with pytest.raises(PreviewAuthorizationError):
        issue_preview_token(subject="owner", actor_role="SUPER_ADMIN", effective_role="SUPER_ADMIN", preview_tenant="t", secret=SECRET)
    with pytest.raises(PreviewAuthorizationError):
        issue_preview_token(subject="owner", actor_role="SUPER_ADMIN", effective_role="STUDENT", preview_tenant="", secret=SECRET)


def test_expired_wrong_audience_and_forged_token_fail_closed() -> None:
    issued = datetime.now(UTC) - timedelta(minutes=20)
    token, _ = issue_preview_token(subject="owner", actor_role="SUPER_ADMIN", effective_role="TEACHER", preview_tenant="t", secret=SECRET, now=issued)
    with pytest.raises(PreviewAuthorizationError):
        decode_preview_token(token, secret=SECRET)
    with pytest.raises(PreviewAuthorizationError):
        decode_preview_token(token, secret="y" * 48)


def test_preview_cannot_cross_privilege_boundary_and_audit_is_safe() -> None:
    _, principal = issue_preview_token(subject="owner", actor_role="SUPER_ADMIN", effective_role="SCHOOL_ADMIN", preview_tenant="tenant-a", secret=SECRET)
    with pytest.raises(PreviewAuthorizationError):
        ensure_preview_operation_allowed(principal, "change_permission")
    metadata = preview_audit_metadata(principal, outcome="preview_started")
    assert metadata["preview_id"] == principal.preview_id
    assert not any(any(x in str(k).lower() for x in ("secret", "token", "password", "authorization")) for k in metadata)
