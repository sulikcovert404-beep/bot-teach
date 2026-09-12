"""Persistence bridge for the existing User/Identity tables."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.channels import Channel, ExternalIdentity
from app.db.models import Identity, User


class DatabaseIdentityResolver:
    """Resolve channel subjects using the existing non-destructive schema."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, provider: Channel, provider_subject: str) -> ExternalIdentity | None:
        row = await self._session.scalar(
            select(Identity).where(
                Identity.provider == provider.value,
                Identity.subject == provider_subject,
            )
        )
        if row is not None:
            return ExternalIdentity(provider, provider_subject, row.user_id, verified=True)
        if provider is Channel.TELEGRAM:
            user = await self._session.scalar(
                select(User).where(User.telegram_user_id == int(provider_subject))
            )
            if user is not None:
                return ExternalIdentity(provider, provider_subject, user.id, verified=True)
        return None

    async def link(
        self, provider: Channel, provider_subject: str, user_id: int, *, verified: bool = False
    ) -> ExternalIdentity:
        existing = await self._session.scalar(
            select(Identity).where(
                Identity.provider == provider.value,
                Identity.subject == provider_subject,
            )
        )
        if existing is not None:
            if existing.user_id != user_id:
                raise ValueError("External identity is already linked to another user")
            return ExternalIdentity(provider, provider_subject, user_id, verified=verified)
        self._session.add(
            Identity(provider=provider.value, subject=provider_subject, user_id=user_id)
        )
        await self._session.flush()
        return ExternalIdentity(provider, provider_subject, user_id, verified=verified)
