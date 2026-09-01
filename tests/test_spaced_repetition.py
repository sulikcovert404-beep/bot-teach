from datetime import UTC, datetime

from app.services.spaced_repetition import schedule_review


def test_good_reviews_grow_interval() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = schedule_review(quality=5, review_count=0, interval_days=0, ease_factor=2.5, now=now)
    second = schedule_review(quality=5, review_count=first.review_count, interval_days=first.interval_days, ease_factor=first.ease_factor, now=now)
    assert first.interval_days == 1
    assert second.interval_days == 6


def test_failed_review_resets_interval() -> None:
    result = schedule_review(quality=1, review_count=4, interval_days=20, ease_factor=2.5, now=datetime(2026, 1, 1, tzinfo=UTC))
    assert result.interval_days == 1
