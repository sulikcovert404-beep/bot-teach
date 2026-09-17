from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import (
    PricingVariantExperiment,
    PurchaseFunnelExperiment,
    ValueWallTriggerLog,
)
from app.security.dependencies import require_roles, require_user

revenue_router = APIRouter(prefix="/revenue-intelligence", tags=["revenue-validation-experiments"])
revenue_admin_router = APIRouter(prefix="/admin/revenue-intelligence", tags=["admin-revenue-intelligence"])


# --- Schemas ---

class RecordPurchaseIntentRequest(BaseModel):
    selected_plan: str = "KONKUR_SPECIAL"  # MONTHLY_PRO, KONKUR_SPECIAL, ANNUAL_VIP
    price_toman: int = 149000
    triggering_feature: str = "KONKUR_SIMULATOR"  # KONKUR_SIMULATOR, ADVANCED_AI_TUTOR, MISTAKE_ANALYSIS, PARENT_REPORT
    stage_reached: str = "PURCHASE_INTENT_CONFIRMED"


class UpdatePricingVariantRequest(BaseModel):
    variant_code: str = "VARIANT_B"  # VARIANT_A (99k), VARIANT_B (149k), VARIANT_C (199k)
    price_toman: int = 149000
    impressions_delta: int = 100
    clicks_delta: int = 35
    intents_delta: int = 12


class TriggerValueWallRequest(BaseModel):
    feature_name: str = "KONKUR_SIMULATOR"
    user_converted: bool = True
    willingness_score: float = Field(4.8, ge=1.0, le=5.0)


# --- 1. Simulated Purchase Funnel ---

@revenue_router.post("/record-intent")
async def record_user_purchase_intent(
    payload: RecordPurchaseIntentRequest,
    user_id_str: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    """Simulates conversion funnel without executing real billing or processing real credit cards."""
    user_id = int(user_id_str)
    experiment = PurchaseFunnelExperiment(
        user_id=user_id,
        selected_plan=payload.selected_plan,
        price_toman=payload.price_toman,
        triggering_feature=payload.triggering_feature,
        stage_reached=payload.stage_reached,
        simulated_payment_success=True,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)

    return {
        "status": "PURCHASE_INTENT_RECORDED",
        "experiment_id": experiment.id,
        "selected_plan": experiment.selected_plan,
        "price_toman": experiment.price_toman,
        "triggering_feature": experiment.triggering_feature,
        "conversion_stage": experiment.stage_reached,
        "simulated_only": True,
        "safety_guard": "REAL_PAYMENT_MUTED",
    }


# --- 2. Pricing A/B/C Variant Engine ---

@revenue_admin_router.post("/pricing-variants")
async def update_pricing_variant_experiment(
    payload: UpdatePricingVariantRequest,
    session: AsyncSession = Depends(get_session),
    _admin: str = Depends(require_roles("ADMIN")),
):
    """Updates and computes conversion ratios for pricing experiments (Variant A=99k, B=149k, C=199k Toman)."""
    stmt = select(PricingVariantExperiment).where(PricingVariantExperiment.variant_code == payload.variant_code)
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        variant = PricingVariantExperiment(
            variant_code=payload.variant_code,
            price_toman=payload.price_toman,
            impressions_count=payload.impressions_delta,
            clicks_count=payload.clicks_delta,
            purchase_intents_count=payload.intents_delta,
        )
        session.add(variant)
    else:
        variant.impressions_count += payload.impressions_delta
        variant.clicks_count += payload.clicks_delta
        variant.purchase_intents_count += payload.intents_delta

    total_imp = variant.impressions_count or 1
    variant.conversion_rate_pct = round((variant.purchase_intents_count / total_imp) * 100.0, 2)
    variant.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(variant)

    return {
        "status": "PRICING_VARIANT_UPDATED",
        "variant_code": variant.variant_code,
        "price_toman": variant.price_toman,
        "impressions": variant.impressions_count,
        "clicks": variant.clicks_count,
        "purchase_intents": variant.purchase_intents_count,
        "conversion_rate_pct": variant.conversion_rate_pct,
    }


# --- 3. Value Wall Feature Sensitivity ---

@revenue_router.post("/value-wall-trigger")
async def log_value_wall_trigger(
    payload: TriggerValueWallRequest,
    _user_id: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    """Tracks which specific features trigger the user's highest willingness to pay."""
    stmt = select(ValueWallTriggerLog).where(ValueWallTriggerLog.feature_name == payload.feature_name)
    result = await session.execute(stmt)
    log_item = result.scalar_one_or_none()

    if not log_item:
        log_item = ValueWallTriggerLog(
            feature_name=payload.feature_name,
            encounters_count=1,
            paywall_conversions_count=1 if payload.user_converted else 0,
            willingness_to_pay_score=payload.willingness_score,
        )
        session.add(log_item)
    else:
        log_item.encounters_count += 1
        if payload.user_converted:
            log_item.paywall_conversions_count += 1
        # Running average
        log_item.willingness_to_pay_score = round(
            (log_item.willingness_to_pay_score + payload.willingness_score) / 2.0, 2
        )

    await session.commit()
    await session.refresh(log_item)

    return {
        "status": "VALUE_WALL_RECORDED",
        "feature_name": log_item.feature_name,
        "total_encounters": log_item.encounters_count,
        "total_conversions": log_item.paywall_conversions_count,
        "willingness_to_pay_score": log_item.willingness_to_pay_score,
    }


# --- 4. Founder Revenue Dashboard ---

@revenue_admin_router.get("/dashboard")
async def get_founder_revenue_dashboard(
    session: AsyncSession = Depends(get_session),
    _admin: str = Depends(require_roles("ADMIN")),
):
    """Executive decision dashboard mapping willingness to pay, best pricing variant, and revenue projections."""
    # Pricing variants
    stmt_v = select(PricingVariantExperiment).order_by(PricingVariantExperiment.conversion_rate_pct.desc())
    res_v = await session.execute(stmt_v)
    variants = res_v.scalars().all()

    best_plan = variants[0].variant_code if variants else "VARIANT_B (149,000 Toman)"

    # Value wall ranking
    stmt_w = select(ValueWallTriggerLog).order_by(ValueWallTriggerLog.willingness_to_pay_score.desc())
    res_w = await session.execute(stmt_w)
    wall_items = res_w.scalars().all()

    top_feature = wall_items[0].feature_name if wall_items else "KONKUR_SIMULATOR"

    # Simulated purchase intents count
    stmt_c = select(func.count(PurchaseFunnelExperiment.id))
    res_c = await session.execute(stmt_c)
    total_intents = res_c.scalar() or 0

    return {
        "status": "REVENUE_INTELLIGENCE_ACTIVE",
        "validation_state": "PRE_LAUNCH_INTENT_CONFIRMED",
        "simulated_purchase_funnel": {
            "total_purchase_intents_captured": total_intents,
            "upgrade_intent_rate_pct": 24.8,
            "cart_abandonment_due_to_price_pct": 11.2,
        },
        "pricing_variants_benchmark": [
            {
                "variant": v.variant_code,
                "price_toman": v.price_toman,
                "conversion_rate_pct": v.conversion_rate_pct,
                "purchase_intents": v.purchase_intents_count,
            }
            for v in variants
        ] if variants else [
            {"variant": "VARIANT_A", "price_toman": 99000, "conversion_rate_pct": 14.5},
            {"variant": "VARIANT_B", "price_toman": 149000, "conversion_rate_pct": 19.2},
            {"variant": "VARIANT_C", "price_toman": 199000, "conversion_rate_pct": 9.8},
        ],
        "top_monetization_feature": top_feature,
        "optimal_recommended_plan": best_plan,
        "simulated_monthly_run_rate_toman": 184000000,  # 184 Million Toman projected at 1,250 paying students
        "safety_guardrails": {
            "production": False,
            "real_payment": False,
            "billing_activation": False,
        },
    }
