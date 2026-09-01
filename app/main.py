from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.admin import router as admin_router
from app.api.routes.ai import router as ai_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.flashcards import router as flashcards_router
from app.api.routes.health import router as health_router
from app.api.routes.sources import router as sources_router
from app.api.routes.study_plan import router as study_plan_router
from app.api.routes.subscriptions import router as subscriptions_router
from app.api.routes.telegram import router as telegram_router
from app.api.routes.tutor import router as tutor_router
from app.api.routes.v1 import router as v1_router
from app.api.routes.worksheets import router as worksheets_router
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware
from app.core.rate_limit import InMemoryRateLimitMiddleware
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


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.include_router(health_router)
app.include_router(v1_router, prefix="/api/v1")
app.include_router(worksheets_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(curriculum_router, prefix="/api/v1")
app.include_router(flashcards_router, prefix="/api/v1")
app.include_router(subscriptions_router, prefix="/api/v1")
app.include_router(study_plan_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(telegram_router, prefix="/api/v1")
app.include_router(tutor_router, prefix="/api/v1")
