import pytest

from app.adapters.telegram import validate_web_app_init_data
from app.domain.entitlements.models import FeatureCode, SubscriptionPlan


def test_subscription_and_feature_codes() -> None:
    assert SubscriptionPlan.FREE.value == "FREE"
    assert FeatureCode.AI_CHAT.value == "AI_CHAT"


def test_telegram_validation_does_not_accept_missing_credentials() -> None:
    with pytest.raises(ValueError):
        validate_web_app_init_data("", "")
