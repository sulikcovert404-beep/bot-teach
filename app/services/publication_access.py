"""Provider-neutral policy decisions for classroom content publication/access."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PublicationContext:
    teacher_id: int
    owner_teacher_id: int | None
    teacher_tenant_id: str | None
    classroom_tenant_id: str | None

def can_publish(ctx: PublicationContext) -> bool:
    return (ctx.owner_teacher_id == ctx.teacher_id and ctx.teacher_tenant_id is not None
            and ctx.teacher_tenant_id == ctx.classroom_tenant_id)

def can_access(*, is_member: bool, has_entitlement: bool, published: bool) -> bool:
    return is_member and has_entitlement and published
