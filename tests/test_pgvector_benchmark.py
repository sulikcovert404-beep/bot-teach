import pytest

from scripts.pgvector_benchmark import percentile


def test_percentile_is_deterministic() -> None:
    assert percentile([3.0, 1.0, 2.0, 4.0], 50) == 2.0
    assert percentile([3.0, 1.0, 2.0, 4.0], 95) == 4.0


def test_percentile_rejects_empty_values() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)
