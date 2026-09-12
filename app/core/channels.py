"""Provider-neutral channel and identity contracts.

Phase 1 intentionally contains contracts only; persistence and provider wiring are
owned by later gates.  Telegram remains supported through its existing adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence
from uuid import UUID


class Channel(StrEnum):
    TELEGRAM = "telegram"
    BALE = "bale"
    WEB = "web"
    ANDROID = "android"


@dataclass(frozen=True)
class ExternalIdentity:
    provider: Channel
    provider_subject: str
    user_id: int | UUID
    verified: bool = False


@dataclass(frozen=True)
class ChannelContext:
    channel: Channel
    user_id: int | UUID | None
    tenant_id: UUID | str | None
    trace_id: str
    locale: str = "fa-IR"


@dataclass(frozen=True)
class CanonicalCommand:
    name: str
    payload: Mapping[str, Any]
    context: ChannelContext
    request_id: str
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ChannelResponse:
    body: Mapping[str, Any]
    status_code: int = 200
    headers: Mapping[str, str] | None = None


class IdentityResolver(Protocol):
    async def resolve(self, provider: Channel, provider_subject: str) -> ExternalIdentity | None: ...

    async def link(
        self, provider: Channel, provider_subject: str, user_id: int | UUID, *, verified: bool = False
    ) -> ExternalIdentity: ...


class ChannelAdapter(Protocol):
    channel: Channel

    async def authenticate(self, event: Mapping[str, Any]) -> ChannelContext: ...

    async def to_command(self, event: Mapping[str, Any], context: ChannelContext) -> CanonicalCommand: ...

    async def render_response(self, response: ChannelResponse) -> Mapping[str, Any]: ...

    async def send_message(self, destination: str, message: str) -> None: ...


class NotificationProvider(Protocol):
    channel: Channel

    async def send(
        self, destination: str, message: str, *, notification_id: str, metadata: Mapping[str, Any] | None = None
    ) -> None: ...


class NotificationService:
    """Provider-neutral notification facade; providers are injected by composition."""

    def __init__(self, providers: Sequence[NotificationProvider]) -> None:
        self._providers = {provider.channel: provider for provider in providers}

    async def send(
        self, channel: Channel, destination: str, message: str, *, notification_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        provider = self._providers.get(channel)
        if provider is None:
            raise LookupError(f"No notification provider for channel: {channel.value}")
        if metadata is None:
            await provider.send(destination, message, notification_id=notification_id)
        else:
            await provider.send(destination, message, notification_id=notification_id, metadata=metadata)
