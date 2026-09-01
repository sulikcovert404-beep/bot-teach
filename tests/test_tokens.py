import pytest
from jwt import InvalidTokenError

from app.security.tokens import create_access_token, decode_access_token


def test_access_token_round_trip() -> None:
    token = create_access_token("user-1", "x" * 32)
    assert decode_access_token(token, "x" * 32) == "user-1"


def test_access_token_rejects_wrong_secret() -> None:
    token = create_access_token("user-1", "x" * 32)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, "y" * 32)
