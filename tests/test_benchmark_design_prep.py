"""Test-only checks for the provider-neutral benchmark design package."""

import hashlib
import json
from pathlib import Path

DATASET = Path("data/rag_eval_v1.json")
EXPECTED_SHA256 = "4c3f3f6d274ec63b563101b170cefae323680fe0bf336a53dca551b116b01470"


def _payload() -> dict[str, object]:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_synthetic_dataset_schema_is_provider_neutral_and_sanitized() -> None:
    payload = _payload()
    assert payload["dataset_version"] == "rag-eval-v1.1-synthetic"
    cases = payload["cases"]
    assert isinstance(cases, list) and cases
    required = {
        "case_id",
        "query",
        "expected_sources",
        "expected_state",
        "provenance",
    }
    states = {"sufficient", "no_source", "conflict"}
    for case in cases:
        assert required <= case.keys()
        assert case["expected_state"] in states
        assert isinstance(case["query"], str) and case["query"].strip()
        assert isinstance(case["expected_sources"], list)
        assert "api_key" not in json.dumps(case).casefold()
        assert "password" not in json.dumps(case).casefold()


def test_dataset_canonical_hash_is_reproducible() -> None:
    payload = _payload()
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == EXPECTED_SHA256


def test_dataset_covers_persian_and_failure_strata() -> None:
    cases = _payload()["cases"]
    provenances = {case["provenance"] for case in cases}
    assert {"synthetic:out-of-corpus", "synthetic:conflict-fixture"} <= provenances
    assert any("zwnj" in value for value in provenances)
    assert any("persian-numeral" in value for value in provenances)
    assert any(case["expected_state"] == "no_source" for case in cases)
    assert any(case["expected_state"] == "conflict" for case in cases)


def test_no_source_cases_have_no_expected_sources() -> None:
    for case in _payload()["cases"]:
        if case["expected_state"] == "no_source":
            assert case["expected_sources"] == []
