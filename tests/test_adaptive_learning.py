from app.services.adaptive_learning import PracticeLevel, recommend_practice_level
from app.services.learning_analytics import LearningSummary


def test_recommend_practice_level_uses_learning_score() -> None:
    assert recommend_practice_level(LearningSummary(0, 0, None)) == PracticeLevel.FOUNDATIONS
    assert recommend_practice_level(LearningSummary(2, 600, 0.5)) == PracticeLevel.FOUNDATIONS
    assert recommend_practice_level(LearningSummary(2, 600, 0.7)) == PracticeLevel.STANDARD
    assert recommend_practice_level(LearningSummary(2, 600, 0.9)) == PracticeLevel.CHALLENGE
