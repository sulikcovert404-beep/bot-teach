from enum import StrEnum

from app.services.learning_analytics import LearningSummary


class PracticeLevel(StrEnum):
    FOUNDATIONS = "FOUNDATIONS"
    STANDARD = "STANDARD"
    CHALLENGE = "CHALLENGE"


def recommend_practice_level(summary: LearningSummary) -> PracticeLevel:
    if summary.event_count == 0 or summary.average_score is None:
        return PracticeLevel.FOUNDATIONS
    if summary.average_score < 0.6:
        return PracticeLevel.FOUNDATIONS
    if summary.average_score < 0.85:
        return PracticeLevel.STANDARD
    return PracticeLevel.CHALLENGE
