from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.logging import request_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", summary="Application request metrics")
async def metrics() -> dict[str, object]:
    return request_metrics.snapshot()


@router.get("/metrics/prometheus", response_class=PlainTextResponse, summary="Prometheus metrics")
async def prometheus_metrics() -> PlainTextResponse:
    return PlainTextResponse(request_metrics.prometheus(), media_type="text/plain; version=0.0.4")
