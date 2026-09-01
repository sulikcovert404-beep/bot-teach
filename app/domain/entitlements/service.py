from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entitlements.models import FeatureCode, SubscriptionPlan


@dataclass(frozen=True)
class Entitlement:
    plan: SubscriptionPlan
    features: frozenset[FeatureCode]

    def allows(self, feature: FeatureCode) -> bool:
        return feature in self.features


_PLAN_FEATURES: dict[SubscriptionPlan, frozenset[FeatureCode]] = {
    SubscriptionPlan.FREE: frozenset({FeatureCode.AI_CHAT, FeatureCode.FLASHCARDS}),
    SubscriptionPlan.STUDENT_PLUS: frozenset(
        {FeatureCode.AI_CHAT, FeatureCode.FLASHCARDS, FeatureCode.SMART_SUMMARY, FeatureCode.QUESTION_GENERATOR}
    ),
    SubscriptionPlan.STUDENT_PRO: frozenset(FeatureCode),
    SubscriptionPlan.TEACHER_PRO: frozenset(
        {FeatureCode.AI_CHAT, FeatureCode.SMART_SUMMARY, FeatureCode.QUESTION_GENERATOR,
         FeatureCode.EXAM_GENERATOR, FeatureCode.EXAM_CORRECTOR, FeatureCode.TEACHER_ASSISTANT}
    ),
    SubscriptionPlan.SCHOOL: frozenset(FeatureCode),
    SubscriptionPlan.ENTERPRISE: frozenset(FeatureCode),
}


def entitlement_for_subscription(
    plan: str, active_until: datetime | None, *, now: datetime | None = None
) -> Entitlement:
    try:
        selected_plan = SubscriptionPlan(plan)
    except ValueError as exc:
        raise ValueError("Unknown subscription plan") from exc
    current = now or datetime.now(UTC)
    if active_until is not None:
        expiry = active_until if active_until.tzinfo else active_until.replace(tzinfo=UTC)
        if expiry <= current:
            selected_plan = SubscriptionPlan.FREE
    return Entitlement(selected_plan, _PLAN_FEATURES[selected_plan])


def require_feature(entitlement: Entitlement, feature: FeatureCode) -> None:
    if not entitlement.allows(feature):
        raise PermissionError(f"Feature not available for plan {entitlement.plan.value}")
