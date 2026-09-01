from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import AuditLog, PaymentTransaction, Subscription
from app.security.dependencies import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    action: str
    resource_type: str
    resource_id: str
    metadata_json: str
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    limit: int
    offset: int


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    provider: str
    provider_transaction_id: str
    amount: int
    currency: str
    status: str
    created_at: datetime


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan: str
    active_until: datetime | None
    created_at: datetime


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    _subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AuditLogListResponse:
    result = await session.scalars(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in result.all()],
        limit=limit,
        offset=offset,
    )


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    _subject: str = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=100),
) -> list[PaymentTransaction]:
    result = await session.scalars(
        select(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).limit(limit)
    )
    return list(result.all())


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    _subject: str = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Subscription]:
    result = await session.scalars(
        select(Subscription).order_by(Subscription.created_at.desc()).limit(limit)
    )
    return list(result.all())
