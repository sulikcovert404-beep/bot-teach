from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SchoolAdminMembership, TeacherProfile
from app.security.principal import CanonicalPrincipal


async def enforce_tenant(principal: CanonicalPrincipal, tenant_id: str | None, session: AsyncSession) -> str | None:
    if principal.role == "SUPER_ADMIN": return tenant_id
    if not tenant_id: raise HTTPException(status_code=403, detail="Tenant context required")
    try:
        subject_id = int(principal.subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=403, detail="Tenant scope denied") from exc
    if principal.role == "SCHOOL_ADMIN":
        owns = await session.scalar(select(SchoolAdminMembership.id).where(
            SchoolAdminMembership.user_id == subject_id,
            SchoolAdminMembership.tenant_id == tenant_id,
            SchoolAdminMembership.status == "ACTIVE",
            SchoolAdminMembership.revoked_at.is_(None),
        ))
    else:
        owns = await session.scalar(select(TeacherProfile.id).where(TeacherProfile.teacher_id == subject_id, TeacherProfile.tenant_id == tenant_id))
    if owns is None: raise HTTPException(status_code=403, detail="Tenant scope denied")
    return tenant_id
