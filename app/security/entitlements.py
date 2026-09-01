from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import Subscription
from app.domain.entitlements.models import FeatureCode
from app.domain.entitlements.service import entitlement_for_subscription
from app.security.dependencies import require_user


def require_feature_access(feature: FeatureCode) -> Callable[..., Awaitable[str]]:
    async def dependency(
        subject: str = Depends(require_user),
        session: AsyncSession = Depends(get_session),  # noqa: B008
    ) -> str:
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid user identity") from exc
        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        entitlement = entitlement_for_subscription(
            subscription.plan if subscription else "FREE",
            subscription.active_until if subscription else None,
        )
        if not entitlement.allows(feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature unavailable: {feature.value}",
            )
        return subject

    return dependency
