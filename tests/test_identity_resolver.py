import pytest

from app.core.channels import Channel
from app.services.identity import DatabaseIdentityResolver


@pytest.mark.asyncio
async def test_unknown_identity_returns_none():
    class Session:
        async def scalar(self, statement):
            return None
    assert await DatabaseIdentityResolver(Session()).resolve(Channel.WEB, "x") is None
