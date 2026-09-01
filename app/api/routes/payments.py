import hmac
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.security.dependencies import require_user
from app.services.payments import apply_payment_callback, create_payment_intent

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIntentRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    amount: int = Field(ge=1)
    plan: str = Field(min_length=1, max_length=32)


class PaymentIntentResponse(BaseModel):
    provider_transaction_id: str
    amount: int
    status: str


class PaymentCallbackRequest(BaseModel):
    provider_transaction_id: str = Field(min_length=1, max_length=255)
    status: Literal["SUCCEEDED", "FAILED"]
    plan: str = Field(min_length=1, max_length=32)
    active_days: int = Field(default=30, ge=1, le=730)


@router.post("/intent", response_model=PaymentIntentResponse)
async def payment_intent(
    request: PaymentIntentRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PaymentIntentResponse:
    try:
        transaction = await create_payment_intent(
            session, user_id=int(subject), provider=request.provider, amount=request.amount, plan=request.plan
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    await session.commit()
    return PaymentIntentResponse(
        provider_transaction_id=transaction.provider_transaction_id,
        amount=transaction.amount,
        status=transaction.status,
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
