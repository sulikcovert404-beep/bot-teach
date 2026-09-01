import pytest

from app.domain.entitlements.models import FeatureCode, SubscriptionPlan
from app.domain.entitlements.service import Entitlement, require_feature


def test_entitlement_allows_declared_feature() -> None:
    entitlement = Entitlement(SubscriptionPlan.STUDENT_PLUS, frozenset({FeatureCode.AI_CHAT}))
    require_feature(entitlement, FeatureCode.AI_CHAT)


def test_entitlement_rejects_missing_feature() -> None:
    entitlement = Entitlement(SubscriptionPlan.FREE, frozenset())
    with pytest.raises(PermissionError):
        require_feature(entitlement, FeatureCode.AI_CHAT)

