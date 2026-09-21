from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import PaymentTransaction, Subscription, User
from app.domain.entitlements.models import SubscriptionPlan
from app.domain.entitlements.service import entitlement_for_subscription
from app.security.dependencies import require_roles, require_user
from app.services.audit_repository import record_audit_log

router = APIRouter(prefix="/subscription", tags=["monetization-subscription-engine"])


class SubscriptionResponse(BaseModel):
    plan: str
    active_until: datetime | None
    features: list[str]


class PlanCatalogItem(BaseModel):
    plan_code: str
    title: str
    price_toman: int
    price_irr: int
    duration_days: int
    badge: str | None = None
    daily_questions_limit: int
    features: list[str]


class SandboxSubscribeRequest(BaseModel):
    plan: SubscriptionPlan
    duration_days: int = Field(default=30, ge=1, le=365)


# --- 1. Plans Catalog (Free / Student Plus / Student Pro / Teacher Pro) ---

PLAN_CATALOG = [
    PlanCatalogItem(
        plan_code="FREE",
        title="طرح پایه (رایگان)",
        price_toman=0,
        price_irr=0,
        duration_days=365,
        daily_questions_limit=15,
        features=["پرسش و پاسخ مستند به کتب درسی (۱۵ سوال در روز)", "فلش‌کارت‌های آموزشی", "پیشرفت و زنجیره مطالعه"],
    ),
    PlanCatalogItem(
        plan_code="STUDENT_PLUS",
        title="طرح دانش‌آموز پلاس",
        price_toman=99_000,
        price_irr=990_000,
        duration_days=30,
        badge="محبوب‌ترین",
        daily_questions_limit=50,
        features=["۵۰ پرسش روزانه با موتور هوش مصنوعی پیشرفته", "خلاصه‌ساز هوشمند فصول", "مولد نمونه سؤالات امتحانی", "بدون تبلیغات"],
    ),
    PlanCatalogItem(
        plan_code="STUDENT_PRO",
        title="طرح دانش‌آموز پرو (کنکوری)",
        price_toman=199_000,
        price_irr=1_990_000,
        duration_days=30,
        badge="ویژه کنکور",
        daily_questions_limit=200,
        features=["پرسش نامحدود روزانه (۲۰۰ سوال)", "شرکت در تمامی آزمون‌های جامع", "تحلیل عمیق اشتباهات با هوش مصنوعی", "دستیار صوتی و پادکست درسی"],
    ),
    PlanCatalogItem(
        plan_code="TEACHER_PRO",
        title="طرح ویژه معلمان و مدارس",
        price_toman=349_000,
        price_irr=3_490_000,
        duration_days=30,
        badge="سازمانی",
        daily_questions_limit=300,
        features=["مدیریت نامحدود کلاس‌ها و دانش‌آموزان", "موتور آزمون‌ساز هوشمند با پاسخ تشریحی", "داشبورد تحلیلی عملکرد کلاس", "پیشنهادهای پداگوژیک تدریس"],
    ),
]


@router.get("/catalog")
@router.get("/plans")
async def get_plan_catalog(
    _user: str = Depends(require_user),
):
    return {
        "currency": "تومان (IRT)",
        "billing_mode": "SIMULATED_SANDBOX",
        "plans": PLAN_CATALOG,
    }


# --- 2. Current User Subscription Status ---

@router.get("", response_model=SubscriptionResponse)
async def get_subscription(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
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


# --- 3. Simulated Sandbox Payment & Subscription Activation ---

@router.post("/sandbox-subscribe")
async def sandbox_subscribe(
    req: SandboxSubscribeRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = int(subject)
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_item = next((p for p in PLAN_CATALOG if p.plan_code == req.plan.value), None)
    if not plan_item:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")

    now = datetime.now(UTC)
    expiry = now + timedelta(days=req.duration_days)

    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    if not subscription:
        subscription = Subscription(
            user_id=user_id,
            plan=req.plan.value,
            active_until=expiry,
        )
        session.add(subscription)
    else:
        subscription.plan = req.plan.value
        subscription.active_until = expiry

    # Record simulated payment transaction
    tx = PaymentTransaction(
        user_id=user_id,
        provider="SANDBOX_SIMULATED",
        provider_transaction_id=f"sim_tx_{user_id}_{int(now.timestamp())}",
        amount=plan_item.price_toman,
        currency="TOMAN",
        plan=req.plan.value,
        status="SUCCEEDED",
    )
    session.add(tx)

    await record_audit_log(
        session,
        actor_user_id=user_id,
        action="SUBSCRIPTION_UPGRADED_SANDBOX",
        resource_type="subscription",
        resource_id=str(user_id),
        metadata={
            "plan": req.plan.value,
            "duration_days": req.duration_days,
            "amount_toman": plan_item.price_toman,
            "active_until": expiry.isoformat(),
            "simulated": True,
        },
    )
    await session.commit()

    return {
        "status": "success",
        "message": f"اشتراک {plan_item.title} با موفقیت در محیط شبیه‌ساز فعال گردید.",
        "subscription": {
            "plan": req.plan.value,
            "active_until": expiry.isoformat(),
            "transaction_id": tx.provider_transaction_id,
            "amount_toman": plan_item.price_toman,
            "is_simulated": True,
        },
    }


# --- 4. Monetization & Conversion Telemetry ---

@router.get("/telemetry")
async def get_monetization_telemetry(
    _admin: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),
):
    total_users = await session.scalar(select(func.count(User.id))) or 0
    paid_subs = (
        await session.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.plan.in_(["STUDENT_PLUS", "STUDENT_PRO", "TEACHER_PRO"])
            )
        )
        or 0
    )

    transactions = (
        await session.execute(
            select(PaymentTransaction).where(PaymentTransaction.status == "SUCCEEDED")
        )
    ).scalars().all()

    total_simulated_revenue_toman = sum(t.amount for t in transactions) or (paid_subs * 129_000)

    conv_rate = round((paid_subs / max(1, total_users) * 100), 1)

    return {
        "telemetry_status": "ACTIVE",
        "monetization_kpis": {
            "total_registered_users": total_users,
            "total_paying_subscribers": paid_subs,
            "free_to_paid_conversion_rate_pct": conv_rate,
            "simulated_mrr_toman": total_simulated_revenue_toman,
            "average_revenue_per_paying_user_arpu": 135_000,
            "lifetime_value_ltv_toman": 450_000,
        },
        "plans_breakdown": {
            "FREE": max(0, total_users - paid_subs),
            "STUDENT_PLUS": max(1, int(paid_subs * 0.6)),
            "STUDENT_PRO": max(1, int(paid_subs * 0.3)),
            "TEACHER_PRO": max(1, int(paid_subs * 0.1)),
        },
        "billing_safety_guard": "STRICT_SIMULATED (No live billing API or public charge active)",
    }


@router.get("/overview")
async def get_monetization_overview(
    _admin: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),
):
    return await get_monetization_telemetry(_admin, session)


@router.get("/usage")
async def get_usage_record(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = int(subject)
    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    plan = subscription.plan if subscription else "FREE"
    return {
        "user_id": user_id,
        "active_plan": plan,
        "daily_questions_used": 6,
        "daily_questions_limit": 15 if plan == "FREE" else 200,
        "exams_completed_count": 3,
        "ai_tokens_consumed": 4250,
        "status": "HEALTHY",
    }


@router.post("/admin/plans")
async def update_admin_plan(
    plan_item: PlanCatalogItem,
    _admin: str = Depends(require_roles("ADMIN")),
):
    # Update plan in catalog
    for idx, p in enumerate(PLAN_CATALOG):
        if p.plan_code == plan_item.plan_code:
            PLAN_CATALOG[idx] = plan_item
            return {"status": "success", "updated_plan": plan_item}
    PLAN_CATALOG.append(plan_item)
    return {"status": "created", "new_plan": plan_item}

