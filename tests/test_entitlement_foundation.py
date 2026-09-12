from datetime import UTC, datetime, timedelta

from app.domain.entitlements.foundation import (
    AccessDecision,
    AccessRequest,
    Plan,
    Role,
    UserEntitlement,
    resolve_access,
)


def _student(**kwargs) -> UserEntitlement:
    return UserEntitlement("u1", Role.STUDENT, Plan.STUDENT_PRO, frozenset({"AI_TUTOR", "FULL_LIBRARY"}), **kwargs)


def test_allows_entitled_action_in_tenant() -> None:
    result = resolve_access(_student(tenant_id="school-a"), AccessRequest("AI_TUTOR", "school-a"))
    assert result.decision is AccessDecision.ALLOW


def test_denies_cross_tenant_access() -> None:
    result = resolve_access(_student(tenant_id="school-a"), AccessRequest("FULL_LIBRARY", "school-b"))
    assert result.decision is AccessDecision.DENY
    assert result.reason == "tenant_boundary"


def test_expiry_precedes_entitlement() -> None:
    now = datetime.now(UTC)
    result = resolve_access(_student(active_until=now - timedelta(seconds=1)), AccessRequest("AI_TUTOR", now=now))
    assert result.decision is AccessDecision.EXPIRED


def test_ai_quota_is_checked_after_entitlement() -> None:
    result = resolve_access(_student(), AccessRequest("AI_TUTOR", quota_available=False))
    assert result.decision is AccessDecision.QUOTA_EXCEEDED
