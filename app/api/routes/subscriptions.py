from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import Subscription
from app.domain.entitlements.service import entitlement_for_subscription
from app.security.dependencies import require_user

router = APIRouter(prefix="/subscription", tags=["subscription"])


class SubscriptionResponse(BaseModel):
    plan: str
    active_until: datetime | None
    features: list[str]


@router.get("", response_model=SubscriptionResponse)
async def get_subscription(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SubscriptionResponse:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    plan = subscription.plan if subscription else "FREE"
    active_until = subscription.active_until if subscription else None
    entitlement = entitlement_for_subscription(plan, active_until, now=datetime.now(UTC))
    return SubscriptionResponse(
        plan=entitlement.plan.value,
        active_until=active_until,
        features=sorted(feature.value for feature in entitlement.features),
    )
