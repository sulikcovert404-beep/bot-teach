import hashlib
from datetime import UTC, datetime
from typing import NamedTuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AIUsageEvent, Subscription, User


class QuotaLimit(NamedTuple):
    daily_questions: int
    daily_tokens: int


PLAN_QUOTAS: dict[str, QuotaLimit] = {
    "FREE": QuotaLimit(daily_questions=15, daily_tokens=30_000),
    "STUDENT_PLUS": QuotaLimit(daily_questions=50, daily_tokens=100_000),
    "STUDENT_PRO": QuotaLimit(daily_questions=200, daily_tokens=500_000),
    "TEACHER_PRO": QuotaLimit(daily_questions=300, daily_tokens=1_000_000),
    "SCHOOL": QuotaLimit(daily_questions=1_000, daily_tokens=5_000_000),
    "ENTERPRISE": QuotaLimit(daily_questions=10_000, daily_tokens=50_000_000),
}

# In-memory fast burst and duplicate guard: user_id -> list of timestamps
_BURST_TRACKER: dict[int, list[float]] = {}
_LAST_QUERY_HASH: dict[int, tuple[str, float]] = {}


def hash_query(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()


async def check_beta_safety_limits(
    session: AsyncSession,
    *,
    user_id: int,
    query: str,
    now: datetime | None = None,
) -> User:
    current_time = now or datetime.now(UTC)
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="حساب کاربری یافت نشد.",
        )

    # 1. Admin exemption
    if user.role in ("ADMIN", "TEACHER_ADMIN"):
        return user

    # 2. Beta Access Control (Status check)
    # Role 'SUSPENDED' or 'BANNED'
    if user.role in ("SUSPENDED", "BANNED"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="دسترسی بتای این حساب کاربری موقتاً مسدود شده است.",
        )

    # 3. Burst & Abuse Protection (Max 3 queries in 10 seconds)
    import time
    mono_now = time.monotonic()
    burst_window = 10.0
    max_burst = 3

    recent_stamps = _BURST_TRACKER.get(user_id, [])
    recent_stamps = [t for t in recent_stamps if mono_now - t < burst_window]
    if len(recent_stamps) >= max_burst:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="سرعت ارسال پرسش‌های شما بیش از حد مجاز است. لطفاً چند ثانیه شکیبا باشید.",
        )
    recent_stamps.append(mono_now)
    _BURST_TRACKER[user_id] = recent_stamps

    # 4. Duplicate Request Protection (same query within 10 seconds)
    q_hash = hash_query(query)
    last_hash_info = _LAST_QUERY_HASH.get(user_id)
    if last_hash_info:
        prev_hash, prev_time = last_hash_info
        if prev_hash == q_hash and (mono_now - prev_time) < 10.0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="این پرسش هم‌اکنون ارسال شده است. لطفاً از ارسال تکراری خودداری کنید.",
            )
    _LAST_QUERY_HASH[user_id] = (q_hash, mono_now)

    # 5. Daily Quota Limit Check
    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    plan = subscription.plan if subscription else "FREE"
    
    # Check expiry if applicable
    if subscription and subscription.active_until:
        expiry = subscription.active_until if subscription.active_until.tzinfo else subscription.active_until.replace(tzinfo=UTC)
        if expiry <= current_time:
            plan = "FREE"

    quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["FREE"])

    # Calculate questions & tokens consumed today (UTC start of day)
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    stats = (
        await session.execute(
            select(
                func.count(AIUsageEvent.id),
                func.coalesce(func.sum(AIUsageEvent.charged_tokens), 0),
            ).where(
                AIUsageEvent.user_id == user_id,
                AIUsageEvent.created_at >= today_start,
                AIUsageEvent.task_type == "ai_tutor",
            )
        )
    ).one()

    questions_today, tokens_today = int(stats[0]), int(stats[1])

    if questions_today >= quota.daily_questions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"سقف مجاز پرسش روزانه شما ({quota.daily_questions} سؤال) به پایان رسیده است. فردا مجدداً امکان پرسش خواهید داشت.",
        )

    if tokens_today >= quota.daily_tokens:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"سقف مجاز مصرف توکن روزانه شما به پایان رسیده است.",
        )

    return user
