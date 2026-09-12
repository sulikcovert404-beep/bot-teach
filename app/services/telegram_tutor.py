from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.models import ClassMembership, Classroom, StudentProfile, Subscription, User
from app.domain.entitlements.models import FeatureCode
from app.domain.entitlements.service import entitlement_for_subscription
from app.services.ai_gateway import GeminiProvider, ModelRouter, ProviderAuthError, ProviderQuotaError, ProviderResponseError, ProviderTransientError, StructuredLoggingAIProviderObserver
from app.services.ai_tutor import AITutor
from app.services.document_ingestion import DatabaseRetriever
from app.services.usage_repository import record_usage


async def resolve_telegram_identity(
    session: AsyncSession, telegram_user_id: int
) -> tuple[User | None, str | None]:
    """Resolve a Telegram subject to its application user and unambiguous tenant.

    A missing or ambiguous membership never falls back to a default tenant.
    Onboarding may create the user later, but scoped operations must treat the
    returned ``None`` tenant as fail-closed.
    """
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if user is None:
        return None, None
    rows = (
        await session.execute(
            select(Classroom.tenant_id)
            .join(ClassMembership, ClassMembership.classroom_id == Classroom.id)
            .join(StudentProfile, StudentProfile.id == ClassMembership.student_id)
            .where(StudentProfile.student_id == user.id)
            .distinct()
        )
    ).scalars().all()
    tenants = {tenant for tenant in rows if tenant}
    return user, next(iter(tenants)) if len(tenants) == 1 else None

async def answer_telegram_text(
    *,
    text: str,
    telegram_user: object,
    session: AsyncSession,
) -> str:
    """Answer a Telegram text message through the same entitled tutor flow."""
    if not isinstance(telegram_user, dict) or not isinstance(telegram_user.get("id"), int):
        return "برای استفاده از دستیار آموزشی، پیام را از یک حساب معتبر تلگرام ارسال کنید."
    telegram_id = telegram_user["id"]
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_id))
    if user is None:
        user = User(
            telegram_user_id=telegram_id,
            username=telegram_user.get("username")
            if isinstance(telegram_user.get("username"), str)
            else None,
        )
        session.add(user)
        await session.flush()
    subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    entitlement = entitlement_for_subscription(
        subscription.plan if subscription else "FREE",
        subscription.active_until if subscription else None,
    )
    if not entitlement.allows(FeatureCode.AI_CHAT):
        return "دسترسی گفت‌وگوی هوشمند برای حساب شما فعال نیست."
    settings = get_settings()
    if not settings.gemini_api_key:
        return "سرویس هوش مصنوعی موقتاً در دسترس نیست."
    try:
        result = await AITutor(
            GeminiProvider(
                settings.gemini_api_key,
                observer=StructuredLoggingAIProviderObserver(),
            ),
            ModelRouter(settings.ai_default_model),
            DatabaseRetriever(session),
        ).answer(text)
    except ProviderQuotaError:
        return "سرویس هوش مصنوعی در حال حاضر به دلیل محدودیت ظرفیت موقتاً در دسترس نیست."
    except ProviderAuthError:
        return "سرویس هوش مصنوعی نیاز به بررسی تنظیمات دارد."
    except (ProviderTransientError, ProviderResponseError):
        return "سرویس هوش مصنوعی موقتاً دچار اختلال شده است."
    requested_tokens = 1_200
    await record_usage(
        session,
        user_id=user.id,
        task_type="ai_tutor",
        model=result.model,
        requested_tokens=requested_tokens,
        charged_tokens=(
            min(result.usage_tokens, requested_tokens)
            if result.usage_tokens is not None
            else requested_tokens
        ),
    )
    await session.commit()
    return result.text
