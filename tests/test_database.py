import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    AuditLog,
    Exam,
    ExamQuestion,
    Flashcard,
    LearningEvent,
    PaymentTransaction,
    Subscription,
    User,
)


@pytest.mark.asyncio
async def test_user_model_round_trip() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(User(telegram_user_id=42, username="student", role="STUDENT"))
        await session.commit()
        result = await session.scalars(select(User).where(User.telegram_user_id == 42))
        assert result.one().username == "student"
        session.add(Flashcard(user_id=1, front="پایتخت ایران؟", back="تهران"))
        await session.commit()
        cards = await session.scalars(select(Flashcard).where(Flashcard.user_id == 1))
        assert cards.one().back == "تهران"
        session.add(Subscription(user_id=1, plan="STUDENT_PLUS"))
        await session.commit()
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == 1))
        assert subscription is not None
        assert subscription.plan == "STUDENT_PLUS"
        exam = Exam(user_id=1, title="آزمون ریاضی")
        exam.questions.append(
            ExamQuestion(prompt="۲+۲؟", options="۲|۳|۴", correct_option="۴", position=1)
        )
        session.add(exam)
        await session.commit()
        loaded_exam = await session.scalar(select(Exam).where(Exam.title == "آزمون ریاضی"))
        assert loaded_exam is not None
        assert loaded_exam.questions[0].correct_option == "۴"
        session.add(LearningEvent(user_id=1, event_type="lesson_completed", duration_seconds=600, score=0.9))
        await session.commit()
        event = await session.scalar(select(LearningEvent).where(LearningEvent.user_id == 1))
        assert event is not None
        assert event.score == 0.9
        session.add(
            PaymentTransaction(
                user_id=1,
                provider="test",
                provider_transaction_id="tx-1",
                amount=1000,
                status="PENDING",
            )
        )
        await session.commit()
        payment = await session.scalar(
            select(PaymentTransaction).where(PaymentTransaction.provider_transaction_id == "tx-1")
        )
        assert payment is not None
        assert payment.status == "PENDING"
        session.add(
            AuditLog(
                actor_user_id=1,
                action="create",
                resource_type="flashcard",
                resource_id="1",
                metadata_json="{}",
            )
        )
        await session.commit()
        audit = await session.scalar(select(AuditLog).where(AuditLog.resource_id == "1"))
        assert audit is not None
        assert audit.action == "create"

    await engine.dispose()
