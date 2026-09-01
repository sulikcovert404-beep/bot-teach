import pytest

from app.services.learning_analytics import LearningEventInput, summarize_learning


def test_summarize_learning_aggregates_events() -> None:
    summary = summarize_learning(
        [LearningEventInput("lesson", 600, 0.8), LearningEventInput("exam", 300, 1.0)]
    )
    assert summary.event_count == 2
    assert summary.total_duration_seconds == 900
    assert summary.average_score == pytest.approx(0.9)


def test_summarize_learning_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        summarize_learning([LearningEventInput("lesson", -1)])
    with pytest.raises(ValueError):
        summarize_learning([LearningEventInput("exam", 1, 1.1)])
