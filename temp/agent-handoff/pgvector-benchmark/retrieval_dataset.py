"""Loading and validating versioned, provider-neutral retrieval benchmark data."""

import json
from pathlib import Path
from typing import Any

from app.services.retrieval_evaluation import EvaluationCase


def load_evaluation_dataset(path: Path) -> tuple[EvaluationCase, ...]:
    """Load a JSON dataset and validate every case before it reaches a benchmark."""
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise TypeError("Dataset must contain a cases list")
    version = payload.get("dataset_version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Dataset version is required")
    cases: list[EvaluationCase] = []
    for item in payload["cases"]:
        if not isinstance(item, dict):
            raise TypeError("Dataset cases must be objects")
        source_values = item.get("expected_sources", [])
        if not isinstance(source_values, list) or not all(isinstance(value, str) for value in source_values):
            raise ValueError("expected_sources must be a list of strings")
        variants = item.get("paraphrase_variants", [])
        if not isinstance(variants, list) or not all(isinstance(value, str) for value in variants):
            raise ValueError("paraphrase_variants must be a list of strings")
        cases.append(
            EvaluationCase(
                query_id=str(item.get("case_id", "")),
                question=str(item.get("query", "")),
                expected_sources=frozenset(source_values),
                subject=item.get("subject"),
                grade=item.get("grade"),
                chapter=item.get("chapter"),
                difficulty=item.get("difficulty"),
                expects_no_source=item.get("expected_state") == "no_source",
                expects_conflict=item.get("expected_state") == "conflict",
                dataset_version=version,
                relevance_type=item.get("relevance_type", "exact"),
                expected_state=item.get("expected_state", "sufficient"),
                expected_answer=item.get("expected_answer"),
                paraphrase_variants=tuple(variants),
                multi_hop_sources=bool(item.get("multi_hop", False)),
                relevance_grade=int(item.get("relevance_grade", 1)),
                provenance=item.get("provenance"),
            )
        )
    return tuple(cases)
