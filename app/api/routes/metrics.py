from fastapi import APIRouter

from app.core.logging import request_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", summary="Application request metrics")
async def metrics() -> dict[str, object]:
    return request_metrics.snapshot()
