import pytest

from app.services.usage import UsageBudget


def test_usage_budget_caps_and_tracks_tokens() -> None:
    budget = UsageBudget(token_limit=100)
    assert budget.reserve(150) == 100
    assert budget.used_tokens == 100


def test_usage_budget_rejects_after_limit() -> None:
    budget = UsageBudget(token_limit=10, used_tokens=10)
    with pytest.raises(PermissionError):
        budget.reserve(1)

