from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import build_session_factory

router = APIRouter(tags=["health"])

EXPECTED_MIGRATION_HEAD = "a8b9c0d1e2f3"


@router.get("/health", summary="Liveness check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness check")
async def readiness() -> dict[str, str]:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        factory = build_session_factory(settings.database_url)
        async with factory() as session:
            await session.execute(text("SELECT 1"))
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            migration_head = result.scalar_one_or_none()
            if migration_head != EXPECTED_MIGRATION_HEAD:
                raise RuntimeError("Database migrations are not at the application head")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "ready", "migration_head": EXPECTED_MIGRATION_HEAD}
