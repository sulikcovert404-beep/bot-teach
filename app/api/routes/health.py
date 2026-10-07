from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import build_session_factory

router = APIRouter(tags=["health"])

EXPECTED_MIGRATION_HEAD = "20261007_0036"


def migration_heads() -> tuple[str, ...]:
    """Resolve terminal migration heads from the deployed migration source."""
    project_root = Path(__file__).resolve().parents[3]
    script = ScriptDirectory.from_config(Config(str(project_root / "alembic.ini")))
    return tuple(sorted(revision.revision for revision in script.get_revisions("heads")))


@router.get("/", summary="Root check")
async def root() -> dict[str, str]:
    return {"status": "ok", "app": get_settings().app_name}


@router.get("/health", summary="Liveness check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness check")
async def readiness() -> dict[str, Any]:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable"
        )
    try:
        writer_identity_verified = False
        factory = build_session_factory(
            settings.database_url,
            settings.writer_admission_enabled,
            settings.writer_generation,
            settings.writer_instance_id,
            settings.writer_database_role,
        )
        async with factory() as session:
            principal = await session.scalar(text("SELECT session_user"))
            if settings.writer_admission_enabled and principal != settings.writer_database_role:
                raise HTTPException(status_code=503, detail="Writer database role mismatch")
            writer_identity_verified = (
                settings.writer_admission_enabled and principal == settings.writer_database_role
            )
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            migration_head = result.scalar_one_or_none()
            expected = settings.expected_migration_head.strip() or EXPECTED_MIGRATION_HEAD
            if not expected or migration_head != expected:
                raise HTTPException(status_code=503, detail="Migration drift / Not ready")
        if settings.redis_url.strip():
            redis = Redis.from_url(settings.redis_url)
            try:
                await redis.ping()
            finally:
                await redis.aclose()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {
        "status": "ready",
        "migration_head": expected,
        "writer_identity_verified": writer_identity_verified,
    }
