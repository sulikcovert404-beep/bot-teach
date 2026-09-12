import pytest
from pydantic import ValidationError

from app.main import app
from app.services.cohort_feedback import FeedbackSubmitRequest


def test_feedback_route_is_registered_with_expected_contract() -> None:
    assert "post" in app.openapi()["paths"]["/api/v1/tutor/feedback"]


def test_feedback_request_rejects_unknown_feedback_type() -> None:
    with pytest.raises(ValidationError):
        FeedbackSubmitRequest(query="سوال", rating=5, feedback_type="unexpected")


def test_feedback_request_accepts_supported_values() -> None:
    request = FeedbackSubmitRequest(
        query="سوال", rating=1, feedback_type="missing_content"
    )
    assert request.feedback_type == "missing_content"
