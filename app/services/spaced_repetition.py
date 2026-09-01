from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ReviewSchedule:
    review_count: int
    interval_days: int
    ease_factor: float
    next_review_at: datetime


def schedule_review(*, quality: int, review_count: int, interval_days: int, ease_factor: float, now: datetime) -> ReviewSchedule:
    if not 0 <= quality <= 5:
        raise ValueError("quality must be between 0 and 5")
    if review_count < 0 or interval_days < 0 or ease_factor < 1.3:
        raise ValueError("invalid review state")
    updated_ease = max(1.3, ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    if quality < 3 or review_count == 0:
        new_interval = 1
    elif review_count == 1:
        new_interval = 6
    else:
        new_interval = max(1, round(interval_days * updated_ease))
    return ReviewSchedule(review_count + 1, new_interval, round(updated_ease, 4), now + timedelta(days=new_interval))
