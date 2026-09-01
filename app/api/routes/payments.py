import hmac
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.domain.entitlements.models import SubscriptionPlan
from app.security.dependencies import require_user
from app.services.payment_provider import HttpPaymentProvider
from app.services.payments import apply_payment_callback, create_payment_intent

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIntentRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    amount: int = Field(ge=1)
    plan: SubscriptionPlan


class PaymentIntentResponse(BaseModel):
    provider_transaction_id: str
    amount: int
    status: str
    checkout_url: str | None = None


class PaymentCallbackRequest(BaseModel):
    provider_transaction_id: str = Field(min_length=1, max_length=255)
    status: Literal["SUCCEEDED", "FAILED"]
    plan: SubscriptionPlan
    active_days: int = Field(default=30, ge=1, le=730)


@router.post("/intent", response_model=PaymentIntentResponse)
async def payment_intent(
    request: PaymentIntentRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PaymentIntentResponse:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    try:
        settings = get_settings()
        payment_provider = (
            HttpPaymentProvider(settings.payment_provider_url, settings.payment_provider_api_key)
            if settings.payment_provider_url.strip()
            else None
        )
        transaction = await create_payment_intent(
            session,
            user_id=user_id,
            provider=request.provider,
            amount=request.amount,
            plan=request.plan,
            payment_provider=payment_provider,
        )
    except (ValueError, TypeError, httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Payment provider unavailable") from exc
    await session.commit()
    return PaymentIntentResponse(
        provider_transaction_id=transaction.provider_transaction_id,
        amount=transaction.amount,
        status=transaction.status,
        checkout_url=transaction.checkout_url,
    )


@router.post("/webhook", response_model=PaymentIntentResponse)
async def payment_webhook(
    request: PaymentCallbackRequest,
    x_payment_webhook_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PaymentIntentResponse:
    expected = get_settings().payment_webhook_secret
    if not expected or not x_payment_webhook_secret or not hmac.compare_digest(
        x_payment_webhook_secret, expected
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payment webhook secret")
    try:
        transaction = await apply_payment_callback(session, **request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if transaction is None:
        raise HTTPException(status_code=404, detail="Payment transaction not found")
    await session.commit()
    return PaymentIntentResponse(
        provider_transaction_id=transaction.provider_transaction_id,
        amount=transaction.amount,
        status=transaction.status,
    )
