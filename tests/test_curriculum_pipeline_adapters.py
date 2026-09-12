from datetime import UTC, datetime

import pytest

from app.services.curriculum_pipeline_adapters import (
    HttpError,
    check_contract_readiness,
    map_pipeline_error,
    preserve_text,
    serialize_payload,
)
from app.services.curriculum_pipeline_api import (
    AuthorizationError,
    CASConflictError,
    DigestMismatchError,
    InvalidStateError,
    RetryableProcessingError,
)


@pytest.mark.parametrize("error,status,code", [
    (AuthorizationError("denied"), 403, "AUTHORIZATION_ERROR"),
    (CASConflictError("changed"), 409, "CAS_CONFLICT"),
    (DigestMismatchError("bad digest"), 422, "DIGEST_MISMATCH"),
    (InvalidStateError("wrong state"), 422, "INVALID_STATE"),
    (RetryableProcessingError("retry"), 503, "PROCESSING_RETRYABLE"),
])
def test_typed_errors_map_at_http_boundary(error, status, code):
    mapped = map_pipeline_error(error)
    assert mapped == HttpError(status, code, str(error), mapped.retryable)


def test_unknown_error_is_sanitized():
    mapped = map_pipeline_error(RuntimeError("secret db details"))
    assert mapped.status == 500
    assert "secret" not in mapped.message


def test_persian_zwnj_rtl_and_math_are_preserved():
    value = "می‌رود \u200f x² + y² = z²"
    assert preserve_text(value) == value


def test_serialize_payload_is_stable_and_preserves_persian():
    value = {"z": "می‌خواند | F=ma", "a": 1, "at": datetime(2026, 9, 3, tzinfo=UTC)}
    encoded = serialize_payload(value)
    assert encoded == '{"a":1,"at":"2026-09-03T00:00:00+00:00","z":"می‌خواند | F=ma"}'
    assert "\\u200c" not in encoded
    assert serialize_payload({"at": value["at"], "z": "می‌خواند | F=ma", "a": 1}) == encoded


def test_contract_readiness_is_non_db_and_explicit():
    status = check_contract_readiness()
    assert status["provider_neutral_boundary"] == "ready"
    assert status["stable_utf8_serialization"] == "ready"
    assert status["database_runtime"] == "blocked_external_dependency"
