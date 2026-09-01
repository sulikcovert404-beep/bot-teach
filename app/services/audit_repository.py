import json
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

_FORBIDDEN_KEY_PARTS = ("password", "secret", "token", "api_key", "authorization")


async def record_audit_log(
    session: AsyncSession,
    *,
    actor_user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: Mapping[str, object] | None = None,
) -> AuditLog:
    payload = metadata or {}
    if any(
        any(part in key.lower() for part in _FORBIDDEN_KEY_PARTS) for key in payload
    ):
        raise ValueError("Sensitive audit metadata is not allowed")
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )
    session.add(log)
    await session.flush()
    return log
