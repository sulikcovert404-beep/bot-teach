"""Narrow application boundary for canonical tenant membership operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class MembershipResult:
    status: str
    user_id: int
    tenant_id: str
    membership_id: int | None = None


class MembershipDenied(ValueError):
    """A database authorization or lifecycle rule denied the operation."""


class MembershipConflict(ValueError):
    """The target already has an incompatible active tenant or key claim."""


def _fingerprint(operation: str, payload: dict[str, object]) -> str:
    canonical = json.dumps(
        {"operation": operation, **payload}, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def _call(
    session: AsyncSession,
    function: str,
    *,
    actor_id: int,
    actor_role: str,
    operation: str,
    idempotency_key: str,
    payload: dict[str, object],
) -> MembershipResult:
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValueError("A valid idempotency key is required")
    correlation_id = str(uuid4())
    try:
        result = await session.scalar(
            text(
                f"SELECT public.{function}(:actor_id, :actor_role, CAST(:payload AS jsonb), "
                ":fingerprint, :idempotency_key, :correlation_id)"
            ),
            {
                "actor_id": actor_id,
                "actor_role": actor_role,
                "payload": json.dumps(payload, separators=(",", ":")),
                "fingerprint": _fingerprint(operation, payload),
                "idempotency_key": idempotency_key,
                "correlation_id": correlation_id,
            },
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        detail = str(getattr(exc, "orig", exc))
        if "tenant_membership_conflict" in detail or "idempotency_conflict" in detail:
            raise MembershipConflict("Membership request conflicts with current state") from exc
        if "tenant_membership_denied" in detail:
            raise MembershipDenied("Membership operation is not authorized") from exc
        if "tenant_membership_not_found" in detail:
            raise LookupError("Membership target was not found") from exc
        raise
    if isinstance(result, str):
        result = json.loads(result)
    return MembershipResult(
        status=str(result["status"]),
        user_id=int(result["user_id"]),
        tenant_id=str(result["tenant_id"]),
        membership_id=int(result["membership_id"]) if result.get("membership_id") else None,
    )


async def bootstrap_school_tenant(
    session: AsyncSession, *, actor_id: int, actor_role: str, idempotency_key: str,
    tenant_id: str, school_name: str, region: str, school_admin_user_id: int,
) -> MembershipResult:
    payload = {
        "tenant_id": tenant_id, "school_name": school_name, "region": region,
        "school_admin_user_id": school_admin_user_id,
    }
    return await _call(
        session, "bootstrap_school_tenant", actor_id=actor_id, actor_role=actor_role,
        operation="TENANT_BOOTSTRAP", idempotency_key=idempotency_key, payload=payload,
    )


async def provision_membership(
    session: AsyncSession, *, actor_id: int, actor_role: str, idempotency_key: str,
    target_user_id: int, tenant_id: str, target_role: str,
) -> MembershipResult:
    payload = {"user_id": target_user_id, "tenant_id": tenant_id, "role": target_role}
    return await _call(
        session, "provision_tenant_membership", actor_id=actor_id, actor_role=actor_role,
        operation="TENANT_MEMBERSHIP_PROVISION", idempotency_key=idempotency_key,
        payload=payload,
    )


async def revoke_membership(
    session: AsyncSession, *, actor_id: int, actor_role: str, idempotency_key: str,
    target_user_id: int, tenant_id: str,
) -> MembershipResult:
    payload = {"user_id": target_user_id, "tenant_id": tenant_id}
    return await _call(
        session, "revoke_tenant_membership", actor_id=actor_id, actor_role=actor_role,
        operation="TENANT_MEMBERSHIP_REVOKE", idempotency_key=idempotency_key,
        payload=payload,
    )
