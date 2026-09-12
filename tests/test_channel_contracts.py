from uuid import uuid4

import pytest

from app.core.channels import (
    Channel,
    ChannelContext,
    NotificationService,
)


class Provider:
    channel = Channel.TELEGRAM

    def __init__(self):
        self.calls = []

    async def send(self, destination, message, *, notification_id):
        self.calls.append((destination, message, notification_id))


@pytest.mark.asyncio
async def test_notification_service_dispatches_by_channel():
    provider = Provider()
    await NotificationService([provider]).send(
        Channel.TELEGRAM, "42", "سلام", notification_id="n-1"
    )
    assert provider.calls == [("42", "سلام", "n-1")]


def test_channel_context_uses_internal_user_identity():
    user_id = uuid4()
    context = ChannelContext(Channel.TELEGRAM, user_id, None, "trace-1")
    assert context.user_id == user_id
    assert context.channel is Channel.TELEGRAM
