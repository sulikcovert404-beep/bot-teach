from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entitlements.models import FeatureCode, SubscriptionPlan
from app.domain.entitlements.service import entitlement_for_subscription


def test_active_subscription_exposes_plan_features() -> None:
    entitlement = entitlement_for_subscription(
        SubscriptionPlan.STUDENT_PLUS,
        datetime.now(UTC) + timedelta(days=1),
    )
    assert entitlement.plan == SubscriptionPlan.STUDENT_PLUS
    assert entitlement.allows(FeatureCode.SMART_SUMMARY)


def test_expired_subscription_falls_back_to_free() -> None:
    entitlement = entitlement_for_subscription(
        "STUDENT_PRO", datetime(2020, 1, 1, tzinfo=UTC), now=datetime(2025, 1, 1, tzinfo=UTC)
    )
    assert entitlement.plan == SubscriptionPlan.FREE
    assert not entitlement.allows(FeatureCode.EXAM_GENERATOR)


def test_unknown_plan_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        entitlement_for_subscription("UNKNOWN", None)
