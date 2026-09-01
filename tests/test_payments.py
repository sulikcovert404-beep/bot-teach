
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import AuditLog, PaymentTransaction, Subscription
from app.services.payments import apply_payment_callback, create_payment_intent


@pytest.mark.asyncio
async def test_payment_callback_is_idempotent_and_activates_subscription() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        transaction = await create_payment_intent(
            session, user_id=7, provider="test", amount=1000, plan="STUDENT_PLUS"
        )
        await session.commit()
        updated = await apply_payment_callback(
            session,
            provider_transaction_id=transaction.provider_transaction_id,
            status="SUCCEEDED",
            plan="STUDENT_PLUS",
        )
        await session.commit()
        repeated = await apply_payment_callback(
            session,
            provider_transaction_id=transaction.provider_transaction_id,
            status="SUCCEEDED",
            plan="STUDENT_PLUS",
        )
        await session.commit()
        assert updated is not None and repeated is not None
        assert repeated.status == "SUCCEEDED"
        subscription = await session.get(Subscription, 1)
        assert subscription is not None
        assert subscription.plan == "STUDENT_PLUS"
        assert subscription.active_until is not None
        assert subscription.active_until.tzinfo is not None or subscription.active_until.tzinfo is None
        loaded = await session.get(PaymentTransaction, transaction.id)
        assert loaded is not None and loaded.status == "SUCCEEDED"
        audit_logs = await session.scalars(AuditLog.__table__.select())
        assert len(audit_logs.all()) == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_payment_callback_rejects_plan_mismatch() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        transaction = await create_payment_intent(
            session, user_id=7, provider="test", amount=1000, plan="STUDENT_PLUS"
        )
        await session.commit()
        with pytest.raises(ValueError, match="plan does not match"):
            await apply_payment_callback(
                session,
                provider_transaction_id=transaction.provider_transaction_id,
                status="SUCCEEDED",
                plan="STUDENT_PRO",
            )
    await engine.dispose()
