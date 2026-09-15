from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from app.core.channels import CanonicalCommand, Channel, ChannelContext, ChannelResponse


class BaleAdapter:
    channel = Channel.BALE

    def __init__(self, *, identity_resolver=None, command_handler: Callable[[CanonicalCommand], Awaitable[ChannelResponse]] | None = None):
        self.identity_resolver = identity_resolver
        self.command_handler = command_handler

    async def authenticate(self, event: Mapping[str, Any]) -> ChannelContext:
        subject = event.get("sender_id")
        if not isinstance(subject, (str, int)) or not str(subject):
            raise ValueError("Bale sender identity is required")
        user_id = None
        if self.identity_resolver is not None:
            identity = await self.identity_resolver.resolve(self.channel, str(subject))
            user_id = identity.user_id if identity is not None else None
        return ChannelContext(channel=self.channel, user_id=user_id, tenant_id=None, trace_id=str(event.get("trace_id", "bale:unattributed")), locale=str(event.get("locale", "fa-IR")))

    async def to_command(self, event: Mapping[str, Any], context: ChannelContext) -> CanonicalCommand:
        return CanonicalCommand(name="bale.message", payload=dict(event), context=context, request_id=str(event.get("update_id", context.trace_id)), idempotency_key=str(event["update_id"]) if event.get("update_id") is not None else None)

    async def handle_event(self, event: Mapping[str, Any]) -> ChannelResponse:
        context = await self.authenticate(event)
        command = await self.to_command(event, context)
        if self.command_handler is None:
            return ChannelResponse(body={"status": "accepted", "command": command.name})
        return await self.command_handler(command)

    async def render_response(self, response: ChannelResponse) -> Mapping[str, Any]:
        return {"text": response.body, "status_code": response.status_code}

    async def send_message(self, destination: str, message: str) -> None:
        raise RuntimeError("Bale transport is intentionally not connected in Phase 4")
