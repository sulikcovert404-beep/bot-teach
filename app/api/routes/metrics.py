from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.logging import request_metrics, telegram_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", summary="Application request metrics")
async def metrics() -> dict[str, object]:
    result = request_metrics.snapshot()
    result["telegram"] = telegram_metrics.snapshot()
    return result


@router.get("/metrics/prometheus", response_class=PlainTextResponse, summary="Prometheus metrics")
async def prometheus_metrics() -> PlainTextResponse:
    body = request_metrics.prometheus() + telegram_metrics.prometheus()
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")
