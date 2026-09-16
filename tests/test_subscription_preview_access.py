from datetime import UTC, datetime, timedelta

from app.domain.entitlements.foundation import (
    ClassroomContentAccess,
    resolve_classroom_content_access,
)


def test_free_member_gets_preview_and_pro_gets_full() -> None:
    assert resolve_classroom_content_access(is_member=True, plan="STUDENT_FREE") == ClassroomContentAccess.PREVIEW
    assert resolve_classroom_content_access(is_member=True, plan="STUDENT_PRO") == ClassroomContentAccess.FULL

def test_membership_precedes_plan_and_expiry_falls_back_to_preview() -> None:
    assert resolve_classroom_content_access(is_member=False, plan="STUDENT_PRO") == ClassroomContentAccess.DENY
    expired = datetime.now(UTC) - timedelta(seconds=1)
    assert resolve_classroom_content_access(is_member=True, plan="STUDENT_PRO", active_until=expired) == ClassroomContentAccess.PREVIEW

def test_unpublished_is_denied_and_missing_subscription_is_safe_preview() -> None:
    assert resolve_classroom_content_access(is_member=True, plan="STUDENT_PRO", published=False) == ClassroomContentAccess.DENY
    assert resolve_classroom_content_access(is_member=True, plan=None) == ClassroomContentAccess.PREVIEW
