from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Identity,
    SchoolAdminMembership,
    SchoolTenant,
    StudentProfile,
    TeacherProfile,
    User,
)
from app.services.audit_repository import record_audit_log


ALLOWED_ROLES = frozenset({"STUDENT", "TEACHER", "SCHOOL_ADMIN"})


@dataclass(frozen=True)
class ProvisioningResult:
    status: str
    user_id: int
    role: str
    tenant_id: str | None
    audit_id: int


class ProvisioningDenied(ValueError):
    pass


async def provision_test_identity(
    session: AsyncSession,
    *,
    actor_user_id: int,
    provider: str,
    subject: str,
    username: str | None,
    role: str,
    tenant_id: str | None,
    audit_reason: str,
    idempotency_key: str,
) -> ProvisioningResult:
    """Create one controlled identity and its scope atomically.

    This service deliberately excludes subscriptions and entitlements.  It is
    intended for a separately authorized pilot-provisioning endpoint.
    """
    provider = provider.strip().lower()
    subject = subject.strip()
    role = role.strip().upper()
    tenant_id = tenant_id.strip() if tenant_id else None
    if not provider or len(provider) > 32 or not subject or len(subject) > 255:
        raise ProvisioningDenied("invalid provider identity")
    if role not in ALLOWED_ROLES:
        raise ProvisioningDenied("role is not provisionable")
    if not audit_reason.strip() or len(audit_reason) > 500:
        raise ProvisioningDenied("audit reason is required")
    if not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ProvisioningDenied("idempotency key is required")
    if role in {"TEACHER", "SCHOOL_ADMIN"} and not tenant_id:
        raise ProvisioningDenied("tenant is required for this role")
    if role == "STUDENT" and tenant_id:
        raise ProvisioningDenied("student provisioning cannot imply tenant scope")

    # The caller must have been checked by the route; retain a non-empty actor
    # invariant here so the service cannot be called anonymously by mistake.
    if actor_user_id <= 0:
        raise ProvisioningDenied("invalid provisioning actor")

    try:
        async with session.begin():
            tenant = None
            if tenant_id:
                tenant = await session.scalar(
                    select(SchoolTenant).where(SchoolTenant.tenant_id == tenant_id)
                )
                if tenant is None:
                    raise ProvisioningDenied("tenant not found")

            identity_row = (
                await session.execute(
                    select(Identity, User)
                    .join(User, User.id == Identity.user_id)
                    .where(Identity.provider == provider, Identity.subject == subject)
                )
            ).first()
            user: User | None = identity_row[1] if identity_row else None
            if user is None and provider == "telegram":
                try:
                    telegram_id = int(subject)
                except ValueError as exc:
                    raise ProvisioningDenied("telegram subject must be numeric") from exc
                user = await session.scalar(
                    select(User).where(User.telegram_user_id == telegram_id)
                )

            if user is not None:
                if user.role != role:
                    raise ProvisioningDenied("existing identity has a different role")
                if role == "TEACHER":
                    profile = await session.scalar(
                        select(TeacherProfile).where(
                            TeacherProfile.teacher_id == user.id,
                            TeacherProfile.tenant_id == tenant_id,
                        )
                    )
                    if profile is None:
                        raise ProvisioningDenied("existing teacher is not bound to tenant")
                elif role == "SCHOOL_ADMIN":
                    membership = await session.scalar(
                        select(SchoolAdminMembership).where(
                            SchoolAdminMembership.user_id == user.id,
                            SchoolAdminMembership.tenant_id == tenant_id,
                            SchoolAdminMembership.status == "ACTIVE",
                            SchoolAdminMembership.revoked_at.is_(None),
                        )
                    )
                    if membership is None:
                        raise ProvisioningDenied("existing admin is not bound to tenant")
                audit = await record_audit_log(
                    session,
                    actor_user_id=actor_user_id,
                    action="TEST_IDENTITY_PROVISIONING_EXISTING",
                    resource_type="user",
                    resource_id=str(user.id),
                    metadata={
                        "provider": provider,
                        "role": role,
                        "tenant_id": tenant_id,
                        "idempotency_key": idempotency_key,
                        "reason": audit_reason,
                    },
                )
                return ProvisioningResult("EXISTING", user.id, role, tenant_id, audit.id)

            user = User(
                telegram_user_id=int(subject) if provider == "telegram" else None,
                username=username.strip() if username else None,
                role=role,
            )
            session.add(user)
            await session.flush()
            session.add(Identity(user_id=user.id, provider=provider, subject=subject))
            if role == "STUDENT":
                session.add(StudentProfile(student_id=user.id))
            elif role == "TEACHER":
                session.add(TeacherProfile(teacher_id=user.id, tenant_id=tenant_id))
            else:
                session.add(
                    SchoolAdminMembership(
                        user_id=user.id,
                        tenant_id=tenant_id,
                        status="ACTIVE",
                        created_by=actor_user_id,
                    )
                )
            audit = await record_audit_log(
                session,
                actor_user_id=actor_user_id,
                action="TEST_IDENTITY_PROVISIONED",
                resource_type="user",
                resource_id=str(user.id),
                metadata={
                    "provider": provider,
                    "role": role,
                    "tenant_id": tenant_id,
                    "idempotency_key": idempotency_key,
                    "reason": audit_reason,
                },
            )
            return ProvisioningResult("CREATED", user.id, role, tenant_id, audit.id)
    except IntegrityError as exc:
        await session.rollback()
        raise ProvisioningDenied("identity already exists or violates a scope constraint") from exc
