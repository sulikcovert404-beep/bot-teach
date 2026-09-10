
## Source: app/security/tokens.py
from datetime import UTC, datetime, timedelta

import jwt


def create_access_token(
    subject: str, secret = [REDACTED], expires_minutes: int = 30, role: str | None = None
) -> str:
    if not secret = [REDACTED]
    if expires_minutes < 1:
        raise ValueError("Token expiration must be positive")
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token = [REDACTED], secret = [REDACTED]
    if not secret = [REDACTED]
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Token subject is missing")
    return subject


def decode_access_token_claims(token = [REDACTED], secret = [REDACTED], object]:
    if not secret = [REDACTED]
    return jwt.decode(token, secret, algorithms=["HS256"])


## Source: app/security/entitlements.py
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import Subscription
from app.domain.entitlements.models import FeatureCode
from app.domain.entitlements.service import entitlement_for_subscription
from app.security.dependencies import require_user


def require_feature_access(feature: FeatureCode) -> Callable[..., Awaitable[str]]:
    async def dependency(
        subject: str = Depends(require_user),
        session: AsyncSession = Depends(get_session),  # noqa: B008
    ) -> str:
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid user identity") from exc
        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        entitlement = entitlement_for_subscription(
            subscription.plan if subscription else "FREE",
            subscription.active_until if subscription else None,
        )
        if not entitlement.allows(feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature unavailable: {feature.value}",
            )
        return subject

    return dependency


## Source: app/security/dependencies.py
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.security.tokens import decode_access_token, decode_access_token_claims

bearer = HTTPBearer(auto_error=False)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        return decode_access_token(credentials.credentials, get_settings().jwt_secret)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


def authorize_role(user_role: str, allowed_roles: set[str]) -> None:
    if user_role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def require_roles(*allowed_roles: str) -> Callable[..., str]:
    allowed = set(allowed_roles)

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
    ) -> str:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )
        try:
            claims = decode_access_token_claims(credentials.credentials, get_settings().jwt_secret)
            subject = claims.get("sub")
            role = claims.get("role")
            if not isinstance(subject, str) or not isinstance(role, str):
                raise TypeError("Token identity or role is missing")
            authorize_role(role, allowed)
            return subject
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from exc

    return dependency


## Source: app/services/identity.py
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

