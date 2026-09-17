from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.security.dependencies import require_roles, require_user
from app.services.audit_repository import record_audit_log

router = APIRouter(prefix="/growth", tags=["growth-referral-engine"])

# In-memory structured growth store for staging simulation
REFERRAL_REGISTRY: dict[int, dict[str, Any]] = {}
INVITES_DB: list[dict[str, Any]] = []
SCHOOL_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "id": "sch-camp-allameh",
        "school_name": "دبیرستان علامه حلی",
        "invite_code": "ALLAMEH-2026",
        "invite_link": "https://t.me/OstadAI_Bot?start=ref_ALLAMEH2026",
        "registered_students": 48,
        "active_students": 42,
        "target_quota": 100,
        "conversion_rate": 87.5,
    },
    {
        "id": "sch-camp-farzanegan",
        "school_name": "دبیرستان فرزانگان ۱",
        "invite_code": "FARZANEGAN-G10",
        "invite_link": "https://t.me/OstadAI_Bot?start=ref_FARZANEGAN10",
        "registered_students": 62,
        "active_students": 56,
        "target_quota": 100,
        "conversion_rate": 90.3,
    }
]


class ReferralCodeResponse(BaseModel):
    user_id: int
    referral_code: str
    telegram_invite_link: str
    successful_invites_count: int
    growth_points_earned: int
    reward_status: str


class CreateReferralRequest(BaseModel):
    custom_suffix: str | None = None


class RedeemReferralRequest(BaseModel):
    referral_code: str


# --- 1. User Referral Code & Status ---

@router.get("/referral", response_model=ReferralCodeResponse)
async def get_or_create_referral(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = int(subject)
    if user_id not in REFERRAL_REGISTRY:
        code = f"REF{user_id:05d}"
        REFERRAL_REGISTRY[user_id] = {
            "user_id": user_id,
            "referral_code": code,
            "telegram_invite_link": f"https://t.me/OstadAI_Bot?start=ref_{code}",
            "successful_invites_count": 3,
            "growth_points_earned": 150,
            "reward_status": "CLAIMABLE_STUDENT_PLUS_DAYS",
        }
    
    data = REFERRAL_REGISTRY[user_id]
    return ReferralCodeResponse(**data)


@router.post("/referral/create")
async def create_custom_referral(
    req: CreateReferralRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = int(subject)
    code = f"REF-{user_id}" + (f"-{req.custom_suffix.upper()}" if req.custom_suffix else "")
    REFERRAL_REGISTRY[user_id] = {
        "user_id": user_id,
        "referral_code": code,
        "telegram_invite_link": f"https://t.me/OstadAI_Bot?start=ref_{code}",
        "successful_invites_count": REFERRAL_REGISTRY.get(user_id, {}).get("successful_invites_count", 0),
        "growth_points_earned": REFERRAL_REGISTRY.get(user_id, {}).get("growth_points_earned", 0),
        "reward_status": "ACTIVE",
    }
    
    await record_audit_log(
        session,
        actor_user_id=user_id,
        action="REFERRAL_CODE_CREATED",
        resource_type="growth",
        resource_id=code,
        metadata={"code": code},
    )
    await session.commit()
    return {"status": "success", "referral": REFERRAL_REGISTRY[user_id]}


@router.post("/referral/redeem")
async def redeem_referral(
    req: RedeemReferralRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    invitee_id = int(subject)
    target_code = req.referral_code.strip().upper()
    
    # Find referrer
    referrer = next((v for v in REFERRAL_REGISTRY.values() if v["referral_code"].upper() == target_code), None)
    referrer_id = referrer["user_id"] if referrer else 90001
    
    inv_record = {
        "invitee_id": invitee_id,
        "referrer_id": referrer_id,
        "code": target_code,
        "timestamp": datetime.now(UTC).isoformat(),
        "reward_granted": True,
    }
    INVITES_DB.append(inv_record)
    
    if referrer_id in REFERRAL_REGISTRY:
        REFERRAL_REGISTRY[referrer_id]["successful_invites_count"] += 1
        REFERRAL_REGISTRY[referrer_id]["growth_points_earned"] += 50

    return {
        "status": "success",
        "message": "کد دعوت با موفقیت اعمال شد. ۵۰ امتیاز رشد و ۳ روز اشتراک هدیه دریافت کردید.",
        "invite_details": inv_record,
    }


# --- 2. Growth Funnel Analytics ---

@router.get("/funnel")
async def get_growth_funnel(
    _admin: str = Depends(require_roles("ADMIN", "TEACHER")),
):
    return {
        "funnel_name": "Standard Student Onboarding & Retention Funnel",
        "stages": [
            {"stage": "VISIT_LANDING", "users_count": 1200, "conversion_pct": 100.0, "dropoff_pct": 0.0},
            {"stage": "TELEGRAM_START", "users_count": 980, "conversion_pct": 81.7, "dropoff_pct": 18.3},
            {"stage": "REGISTRATION_ROLE", "users_count": 860, "conversion_pct": 71.7, "dropoff_pct": 12.2},
            {"stage": "FIRST_QUESTION_AI", "users_count": 740, "conversion_pct": 61.7, "dropoff_pct": 14.0},
            {"stage": "FIRST_EXAM_COMPLETED", "users_count": 520, "conversion_pct": 43.3, "dropoff_pct": 29.7},
            {"stage": "7_DAY_RETURN_STREAK", "users_count": 410, "conversion_pct": 34.2, "dropoff_pct": 21.2},
            {"stage": "UPGRADE_INTENT_PLAN", "users_count": 135, "conversion_pct": 11.2, "dropoff_pct": 67.1},
        ],
        "overall_activation_rate_pct": 61.7,
        "weekly_retention_rate_pct": 78.8,
    }


# --- 3. Campaign & School Growth Engine ---

@router.get("/schools")
async def get_school_campaigns(
    _admin: str = Depends(require_roles("ADMIN", "TEACHER")),
):
    return {
        "campaigns_count": len(SCHOOL_CAMPAIGNS),
        "total_onboarded_students": sum(c["registered_students"] for c in SCHOOL_CAMPAIGNS),
        "total_active_students": sum(c["active_students"] for c in SCHOOL_CAMPAIGNS),
        "school_campaigns": SCHOOL_CAMPAIGNS,
    }


# --- 4. Retention Intelligence & Churn Risk Analysis ---

@router.get("/retention-intelligence")
async def get_retention_intelligence(
    _admin: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),
):
    return {
        "intelligence_status": "ACTIVE",
        "analyzed_cohort_size": 80,
        "user_segments": {
            "HIGHLY_ACTIVE": {"count": 42, "pct": 52.5, "action": "Offer Referral Reward & Study Leaderboard"},
            "STEADY_LEARNER": {"count": 26, "pct": 32.5, "action": "Recommend Daily 5-min Flashcard Routine"},
            "AT_CHURN_RISK": {"count": 12, "pct": 15.0, "action": "Automated Re-engagement Notification with Personalized Review Path"},
        },
        "sample_risk_users": [
            {
                "user_id": 777102,
                "name": "محمدرضا کاظمی",
                "days_inactive": 8,
                "previous_streak": 5,
                "churn_risk_level": "HIGH",
                "recommended_intervention": "ارسال آزمون شبیه‌ساز ۲ سوالی شیمی با حل تشریحی جهت بازگردانی زنجیره",
            },
            {
                "user_id": 777105,
                "name": "سارا افشار",
                "days_inactive": 6,
                "previous_streak": 12,
                "churn_risk_level": "MEDIUM",
                "recommended_intervention": "نوتیفیکیشن یادآوری رتبه در لیدربورد کلاس و امتیازات باقی‌مانده",
            }
        ]
    }


# --- 5. Overall Growth Analytics Dashboard ---

@router.get("/analytics")
async def get_growth_analytics(
    _admin: str = Depends(require_roles("ADMIN", "TEACHER")),
):
    return {
        "kpis": {
            "viral_coefficient_k_factor": 1.28,
            "referral_invites_sent": 340,
            "referral_signups_completed": 218,
            "referral_conversion_rate_pct": 64.1,
            "top_acquisition_channel": "Telegram School Groups & Peer Referrals",
            "retention_30d_pct": 48.5,
        },
        "growth_status": "EXPONENTIATING_SIMULATED",
        "guard": "STRICT_SIMULATION_STAGING",
    }
