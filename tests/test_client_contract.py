import pytest

from app.core.client_contract import ApiError, AuthChannel, SessionContext


def test_api_error_normalization_marks_retryable_failures():
    error = ApiError.from_response(503, {"code": "UPSTREAM", "detail": "موقتاً در دسترس نیست"})
    assert error.retryable is True
    assert error.code == "UPSTREAM"


def test_session_context_is_channel_neutral():
    context = SessionContext(user_id=7, channel=AuthChannel.WEB)
    assert context.user_id == 7
    assert context.channel is AuthChannel.WEB
