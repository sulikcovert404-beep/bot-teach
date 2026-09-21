from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.adaptive import adaptive_admin_router, adaptive_student_router
from app.api.routes.admin import router as admin_router
from app.api.routes.admin_content import router as admin_content_router
from app.api.routes.advanced_tutor import advanced_tutor_admin_router, advanced_tutor_router
from app.api.routes.agent_orchestration import agents_admin_router
from app.api.routes.ai import router as ai_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.collaboration import parent_router, school_router
from app.api.routes.collaborative_network import collaborative_admin_router, collaborative_router
from app.api.routes.controlled_beta_cohort import cohort_admin_router, cohort_router
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.customer_success import customer_success_router, support_ticket_router
from app.api.routes.data_governance import data_governance_admin_router, data_governance_router
from app.api.routes.day0_operations import day0_admin_router
from app.api.routes.digital_twin import digital_twin_admin_router, digital_twin_router
from app.api.routes.enterprise_success import enterprise_router
from app.api.routes.exams import router as exams_router
from app.api.routes.experiments import decision_admin_router, events_router
from app.api.routes.feedback_iteration import feedback_admin_router
from app.api.routes.flashcards import router as flashcards_router
from app.api.routes.go_to_market import gtm_admin_router, gtm_router
from app.api.routes.growth import router as growth_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge_graph import knowledge_admin_router, knowledge_graph_router
from app.api.routes.market_validation import market_val_admin_router, market_val_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.observability import router as observability_router
from app.api.routes.operations_autonomy import operations_autonomy_router
from app.api.routes.outcome_prediction import prediction_admin_router, prediction_router
from app.api.routes.payments import router as payments_router
from app.api.routes.pilot_preparation import pilot_admin_router, pilot_router
from app.api.routes.product_decision_engine import decision_engine_admin_router
from app.api.routes.product_market_fit import pmf_admin_router, pmf_router
from app.api.routes.production_transition import transition_admin_router
from app.api.routes.resilience_hardening import resilience_admin_router
from app.api.routes.revenue_intelligence import revenue_admin_router, revenue_router
from app.api.routes.scale_operations_intelligence import scale_ops_admin_router, scale_ops_router
from app.api.routes.school_operations import school_ops_router
from app.api.routes.self_optimizing import self_optimizing_admin_router, self_optimizing_router
from app.api.routes.sources import router as sources_router
from app.api.routes.strategy import strategy_router
from app.api.routes.student import router as student_router
from app.api.routes.study_plan import router as study_plan_router
from app.api.routes.subscriptions import router as subscriptions_router
from app.api.routes.teacher import router as teacher_router
from app.api.routes.telegram import router as telegram_router
from app.api.routes.trust_safety import trust_admin_router
from app.api.routes.tutor import router as tutor_router
from app.api.routes.v1 import router as v1_router
from app.api.routes.worksheets import router as worksheets_router
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware
from app.core.rate_limit import InMemoryRateLimitMiddleware, RedisRateLimitMiddleware
from app.db.base import build_session_factory, dispose_session_factory

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    factory = build_session_factory(settings.database_url) if settings.database_url else None
    try:
        yield
    finally:
        if factory is not None:
            await dispose_session_factory(factory)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.mount("/mini-app", StaticFiles(directory="web/mini-app", html=True), name="mini-app")
    app.mount(
        "/admin-dashboard", StaticFiles(directory="web/admin", html=True), name="admin-dashboard"
    )
    app.mount(
        "/teacher-dashboard",
        StaticFiles(directory="web/teacher", html=True),
        name="teacher-dashboard",
    )
    app.mount(
        "/student-dashboard",
        StaticFiles(directory="web/student", html=True),
        name="student-dashboard",
    )
    app.mount("/platform", StaticFiles(directory="web/platform", html=True), name="platform")
    app.add_middleware(RequestLoggingMiddleware)
    if settings.cors_allowed_origins.strip():
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                origin.strip()
                for origin in settings.cors_allowed_origins.split(",")
                if origin.strip()
            ],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Telegram-Bot-Api-Secret-Token",
                "X-Payment-Webhook-Secret",
            ],
        )
    if settings.redis_url.strip():
        app.add_middleware(
            RedisRateLimitMiddleware,
            redis_url=settings.redis_url,
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    else:
        app.add_middleware(
            InMemoryRateLimitMiddleware,
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(worksheets_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    app.include_router(exams_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(admin_content_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(curriculum_router, prefix="/api/v1")
    app.include_router(flashcards_router, prefix="/api/v1")
    app.include_router(subscriptions_router, prefix="/api/v1")
    app.include_router(study_plan_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(telegram_router, prefix="/api/v1")
    app.include_router(teacher_router, prefix="/api/v1")
    app.include_router(tutor_router, prefix="/api/v1")
    app.include_router(student_router, prefix="/api/v1")
    app.include_router(growth_router, prefix="/api/v1")
    app.include_router(growth_router, prefix="/api/v1/admin/growth")
    app.include_router(observability_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(decision_admin_router, prefix="/api/v1")
    app.include_router(adaptive_student_router, prefix="/api/v1")
    app.include_router(adaptive_admin_router, prefix="/api/v1")
    app.include_router(parent_router, prefix="/api/v1")
    app.include_router(school_router, prefix="/api/v1")
    app.include_router(operations_autonomy_router, prefix="/api/v1")
    app.include_router(strategy_router, prefix="/api/v1")
    app.include_router(customer_success_router, prefix="/api/v1")
    app.include_router(support_ticket_router, prefix="/api/v1")
    app.include_router(advanced_tutor_router, prefix="/api/v1")
    app.include_router(advanced_tutor_admin_router, prefix="/api/v1")
    app.include_router(knowledge_graph_router, prefix="/api/v1")
    app.include_router(knowledge_admin_router, prefix="/api/v1")
    app.include_router(prediction_router, prefix="/api/v1")
    app.include_router(prediction_admin_router, prefix="/api/v1")
    app.include_router(digital_twin_router, prefix="/api/v1")
    app.include_router(digital_twin_admin_router, prefix="/api/v1")
    app.include_router(self_optimizing_router, prefix="/api/v1")
    app.include_router(self_optimizing_admin_router, prefix="/api/v1")
    app.include_router(collaborative_router, prefix="/api/v1")
    app.include_router(collaborative_admin_router, prefix="/api/v1")
    app.include_router(data_governance_router, prefix="/api/v1")
    app.include_router(data_governance_admin_router, prefix="/api/v1")
    app.include_router(pmf_router, prefix="/api/v1")
    app.include_router(pmf_admin_router, prefix="/api/v1")
    app.include_router(revenue_router, prefix="/api/v1")
    app.include_router(revenue_admin_router, prefix="/api/v1")
    app.include_router(gtm_router, prefix="/api/v1")
    app.include_router(gtm_admin_router, prefix="/api/v1")
    app.include_router(pilot_router, prefix="/api/v1")
    app.include_router(pilot_admin_router, prefix="/api/v1")
    app.include_router(transition_admin_router, prefix="/api/v1")
    app.include_router(resilience_admin_router, prefix="/api/v1")
    app.include_router(day0_admin_router, prefix="/api/v1")
    app.include_router(feedback_admin_router, prefix="/api/v1")
    app.include_router(decision_engine_admin_router, prefix="/api/v1")
    app.include_router(trust_admin_router, prefix="/api/v1")
    app.include_router(agents_admin_router, prefix="/api/v1")
    app.include_router(school_ops_router, prefix="/api/v1")
    app.include_router(enterprise_router, prefix="/api/v1")
    app.include_router(cohort_router, prefix="/api/v1")
    app.include_router(cohort_admin_router, prefix="/api/v1")
    app.include_router(scale_ops_router, prefix="/api/v1")
    app.include_router(scale_ops_admin_router, prefix="/api/v1")
    app.include_router(market_val_router, prefix="/api/v1")
    app.include_router(market_val_admin_router, prefix="/api/v1")
    from app.api.routes.controlled_external_beta import (
        external_beta_admin_router,
        external_beta_router,
    )

    app.include_router(external_beta_router, prefix="/api/v1")
    app.include_router(external_beta_admin_router, prefix="/api/v1")
    from app.api.routes.public_launch_readiness import (
        public_launch_admin_router,
        public_launch_router,
    )

    app.include_router(public_launch_router, prefix="/api/v1")
    app.include_router(public_launch_admin_router, prefix="/api/v1")
    from app.api.routes.controlled_public_release import (
        controlled_release_admin_router,
        controlled_release_router,
    )

    app.include_router(controlled_release_router, prefix="/api/v1")
    app.include_router(controlled_release_admin_router, prefix="/api/v1")
    from app.api.routes.growth_scale_operations import (
        growth_scale_admin_router,
        growth_scale_router,
    )

    app.include_router(growth_scale_router, prefix="/api/v1")
    app.include_router(growth_scale_admin_router, prefix="/api/v1")
    from app.api.routes.business_revenue_readiness import (
        biz_readiness_admin_router,
        biz_readiness_router,
    )

    app.include_router(biz_readiness_router, prefix="/api/v1")
    app.include_router(biz_readiness_admin_router, prefix="/api/v1")
    from app.api.routes.operational_excellence import (
        ops_excellence_admin_router,
        ops_excellence_router,
    )

    app.include_router(ops_excellence_router, prefix="/api/v1")
    app.include_router(ops_excellence_admin_router, prefix="/api/v1")
    from app.api.routes.phase2_scale_gateway import phase2_scale_admin_router, phase2_scale_router

    app.include_router(phase2_scale_router, prefix="/api/v1")
    app.include_router(phase2_scale_admin_router, prefix="/api/v1")
    from app.api.routes.preprod_gate_audit import preprod_audit_admin_router, preprod_audit_router

    app.include_router(preprod_audit_router, prefix="/api/v1")
    app.include_router(preprod_audit_admin_router, prefix="/api/v1")
    from app.api.routes.production_provisioning import prod_infra_admin_router, prod_infra_router

    app.include_router(prod_infra_router, prefix="/api/v1")
    app.include_router(prod_infra_admin_router, prefix="/api/v1")
    from app.api.routes.vps_canary_deployment import vps_deploy_admin_router, vps_deploy_router

    app.include_router(vps_deploy_router, prefix="/api/v1")
    app.include_router(vps_deploy_admin_router, prefix="/api/v1")
    from app.api.routes.stage3_controlled_onboarding import stage3_admin_router, stage3_router

    app.include_router(stage3_router, prefix="/api/v1")
    app.include_router(stage3_admin_router, prefix="/api/v1")
    from app.api.routes.stage4_controlled_expansion import stage4_admin_router, stage4_router

    app.include_router(stage4_router, prefix="/api/v1")
    app.include_router(stage4_admin_router, prefix="/api/v1")
    from app.api.routes.stage5_controlled_validation import stage5_admin_router, stage5_router

    app.include_router(stage5_router, prefix="/api/v1")
    app.include_router(stage5_admin_router, prefix="/api/v1")
    from app.api.routes.public_beta_preparation import (
        public_beta_prep_admin_router,
        public_beta_prep_router,
    )

    app.include_router(public_beta_prep_router, prefix="/api/v1")
    app.include_router(public_beta_prep_admin_router, prefix="/api/v1")
    from app.api.routes.beta_1000_expansion import (
        beta_expansion_admin_router,
        beta_expansion_router,
    )

    app.include_router(beta_expansion_router, prefix="/api/v1")
    app.include_router(beta_expansion_admin_router, prefix="/api/v1")
    from app.api.routes.commercial_readiness import (
        commercial_prep_admin_router,
        commercial_prep_router,
    )

    app.include_router(commercial_prep_router, prefix="/api/v1")
    app.include_router(commercial_prep_admin_router, prefix="/api/v1")
    from app.api.routes.public_beta_operational_monitoring import (
        ops_monitoring_admin_router,
        ops_monitoring_router,
    )

    app.include_router(ops_monitoring_router, prefix="/api/v1")
    app.include_router(ops_monitoring_admin_router, prefix="/api/v1")

    return app


app = create_app()
