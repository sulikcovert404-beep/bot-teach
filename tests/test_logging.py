import logging

from app.core.logging import configure_ai_provider_logging
from app.services.ai_gateway import AIProviderEvent, StructuredLoggingAIProviderObserver


def test_ai_provider_logging_is_info_and_idempotent(caplog) -> None:
    logger = configure_ai_provider_logging()
    configure_ai_provider_logging()

    event = AIProviderEvent(
        event_type="ai_request_failed",
        provider="gemini",
        model="gemini-test",
        task_type="general",
        status="failed",
        duration_ms=12.5,
        error_type="ProviderQuotaError",
    )
    with caplog.at_level(logging.INFO, logger="education.ai_provider"):
        StructuredLoggingAIProviderObserver(logger).emit(event)

    assert logger.getEffectiveLevel() == logging.INFO
    records = [r for r in caplog.records if r.name == "education.ai_provider"]
    assert len(records) == 1
    assert "ai_provider_event=" in records[0].message
    assert all(secret not in records[0].message.lower() for secret in ("private prompt", "answer text", "api_key"))
