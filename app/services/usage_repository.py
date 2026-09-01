from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AIUsageEvent


async def record_usage(
    session: AsyncSession,
    *,
    user_id: int | None,
    task_type: str,
    model: str,
    requested_tokens: int,
    charged_tokens: int,
) -> AIUsageEvent:
    if requested_tokens < 1 or charged_tokens < 0 or charged_tokens > requested_tokens:
        raise ValueError("Invalid usage values")
    event = AIUsageEvent(
        user_id=user_id,
        task_type=task_type,
        model=model,
        requested_tokens=requested_tokens,
        charged_tokens=charged_tokens,
    )
    session.add(event)
    await session.flush()
    return event

