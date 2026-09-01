from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.domain.entitlements.models import FeatureCode
from app.security.entitlements import require_feature_access


class FakeSession:
    def __init__(self, subscription) -> None:
        self.subscription = subscription

    async def scalar(self, _query):
        return self.subscription


class SubscriptionStub:
    plan = "STUDENT_PLUS"
    active_until = datetime.now(UTC) + timedelta(days=1)


@pytest.mark.asyncio
async def test_feature_dependency_allows_active_plan() -> None:
    dependency = require_feature_access(FeatureCode.SMART_SUMMARY)
    assert await dependency("12", FakeSession(SubscriptionStub())) == "12"


@pytest.mark.asyncio
async def test_feature_dependency_rejects_free_plan() -> None:
    dependency = require_feature_access(FeatureCode.SMART_SUMMARY)
    with pytest.raises(HTTPException) as error:
        await dependency("12", FakeSession(None))
    assert error.value.status_code == 403
