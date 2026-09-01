from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentTransaction, Subscription


async def create_payment_intent(
    session: AsyncSession, *, user_id: int, provider: str, amount: int, plan: str
) -> PaymentTransaction:
    if amount < 1 or not provider.strip() or not plan.strip():
        raise ValueError("Payment intent fields are invalid")
    transaction = PaymentTransaction(
        user_id=user_id,
        provider=provider,
        provider_transaction_id=f"intent-{uuid4().hex}",
        amount=amount,
        status="PENDING",
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def apply_payment_callback(
    session: AsyncSession,
    *,
    provider_transaction_id: str,
    status: str,
    plan: str,
    active_days: int = 30,
) -> PaymentTransaction | None:
    if status not in {"SUCCEEDED", "FAILED"} or not 1 <= active_days <= 730:
        raise ValueError("Payment callback fields are invalid")
    transaction = await session.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.provider_transaction_id == provider_transaction_id
        )
    )
    if transaction is None:
        return None
    if transaction.status == "SUCCEEDED":
        return transaction
    transaction.status = status
    if status == "SUCCEEDED":
        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == transaction.user_id)
        )
        if subscription is None:
            subscription = Subscription(user_id=transaction.user_id)
            session.add(subscription)
        subscription.plan = plan
        subscription.active_until = datetime.now(UTC) + timedelta(days=active_days)
    await session.flush()
    return transaction
