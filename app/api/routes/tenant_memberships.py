"""Canonical, server-authorized tenant membership lifecycle endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.security.canonical import canonical_role
from app.security.dependencies import bearer
from app.security.tokens import decode_access_token_claims
from app.services.tenant_membership import (
    MembershipConflict,
    MembershipDenied,
    bootstrap_school_tenant,
    provision_membership,
    revoke_membership,
)

router = APIRouter(prefix="/admin/tenants", tags=["tenant-memberships"])


@dataclass(frozen=True)
class Actor:
    user_id: int
    role: str


async def authenticated_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
) -> Actor:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        claims = decode_access_token_claims(credentials.credentials, get_settings().jwt_secret)
        subject = claims.get("sub")
        role = canonical_role(claims.get("role"))
        user_id = int(subject) if isinstance(subject, str) else 0
        if user_id <= 0:
            raise ValueError("invalid subject")
        return Actor(user_id=user_id, role=role)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


class BootstrapTenantRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    school_name: str = Field(min_length=1, max_length=150)
    region: str = Field(default="", max_length=100)
    school_admin_user_id: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ProvisionMembershipRequest(BaseModel):
    user_id: int = Field(gt=0)
    role: str = Field(pattern=r"^(STUDENT|TEACHER|SCHOOL_ADMIN)$")
    idempotency_key: str = Field(min_length=1, max_length=128)


class RevokeMembershipRequest(BaseModel):
    user_id: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


def _raise_http(exc: Exception) -> None:
    detail = str(getattr(exc, "orig", exc))
    if isinstance(exc, MembershipDenied) or "tenant_membership_denied" in detail:
        raise HTTPException(status_code=403, detail="Membership operation denied") from exc
    if isinstance(exc, MembershipConflict) or "tenant_membership_conflict" in detail or "idempotency_conflict" in detail:
        raise HTTPException(status_code=409, detail="Membership state conflicts with request") from exc
    if isinstance(exc, LookupError) or "tenant_membership_not_found" in detail:
        raise HTTPException(status_code=404, detail="Tenant or user not found") from exc
    raise exc


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
async def bootstrap_tenant(
    payload: BootstrapTenantRequest,
    actor: Actor = Depends(authenticated_actor),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    try:
        result = await bootstrap_school_tenant(
            session, actor_id=actor.user_id, actor_role=actor.role,
            idempotency_key=payload.idempotency_key, tenant_id=payload.tenant_id,
            school_name=payload.school_name, region=payload.region,
            school_admin_user_id=payload.school_admin_user_id,
        )
    except (MembershipConflict, MembershipDenied, LookupError) as exc:
        _raise_http(exc)
    return result.__dict__


@router.post("/{tenant_id}/memberships", status_code=status.HTTP_201_CREATED)
async def create_membership(
    tenant_id: str,
    payload: ProvisionMembershipRequest,
    actor: Actor = Depends(authenticated_actor),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    try:
        result = await provision_membership(
            session, actor_id=actor.user_id, actor_role=actor.role,
            idempotency_key=payload.idempotency_key, target_user_id=payload.user_id,
            tenant_id=tenant_id, target_role=payload.role,
        )
    except (MembershipConflict, MembershipDenied, LookupError) as exc:
        _raise_http(exc)
    return result.__dict__


@router.get("/{tenant_id}/memberships/{user_id}")
async def read_membership(
    tenant_id: str,
    user_id: int,
    actor: Actor = Depends(authenticated_actor),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    if actor.role not in {"SUPER_ADMIN", "SCHOOL_ADMIN"}:
        raise HTTPException(status_code=403, detail="Membership operation denied")
    try:
        result = await session.scalar(
            text("SELECT public.get_tenant_membership(:actor_id,:actor_role,:user_id,:tenant_id)"),
            {"actor_id": actor.user_id, "actor_role": actor.role,
             "user_id": user_id, "tenant_id": tenant_id},
        )
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        _raise_http(exc)
    return result


@router.delete("/{tenant_id}/memberships/{user_id}")
async def delete_membership(
    tenant_id: str,
    user_id: int,
    actor: Actor = Depends(authenticated_actor),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
):
    try:
        result = await revoke_membership(
            session, actor_id=actor.user_id, actor_role=actor.role,
            idempotency_key=idempotency_key, target_user_id=user_id, tenant_id=tenant_id,
        )
    except (MembershipConflict, MembershipDenied, LookupError) as exc:
        _raise_http(exc)
    return result.__dict__
