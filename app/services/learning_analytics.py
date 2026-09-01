from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class LearningEventInput:
    event_type: str
    duration_seconds: int
    score: float | None = None


@dataclass(frozen=True)
class LearningSummary:
    event_count: int
    total_duration_seconds: int
    average_score: float | None


def summarize_learning(events: Iterable[LearningEventInput]) -> LearningSummary:
    materialized = list(events)
    if any(event.duration_seconds < 0 for event in materialized):
        raise ValueError("Event duration cannot be negative")
    scored = [event.score for event in materialized if event.score is not None]
    if any(score < 0 or score > 1 for score in scored):
        raise ValueError("Scores must be between 0 and 1")
    return LearningSummary(
        event_count=len(materialized),
        total_duration_seconds=sum(event.duration_seconds for event in materialized),
        average_score=sum(scored) / len(scored) if scored else None,
    )
