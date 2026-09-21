from __future__ import annotations

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("mypy_ratchet", Path("scripts/check_mypy_baseline.py"))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

F = ("app/example.py", 4, 2, "arg-type", "Argument 1 has incompatible type")
G = ("app/example.py", 9, 1, "operator", "Unsupported operand types")


def test_exact_and_reordered_pass() -> None:
    assert MODULE.compare([F, G], [G, F]) == (set(), set(), 0)


def test_new_finding_fails() -> None:
    assert MODULE.compare([F, G], [F]) == ({G}, set(), 0)


def test_resolved_finding_fails_without_baseline_update() -> None:
    assert MODULE.compare([F], [F, G]) == (set(), {G}, 0)


def test_same_count_replacement_fails() -> None:
    assert MODULE.compare([F], [G]) == ({F}, {G}, 0)


def test_duplicate_current_fails() -> None:
    new, resolved, duplicates = MODULE.compare([F, F], [F])
    assert (new, resolved, duplicates) == (set(), set(), 1)


def test_duplicate_baseline_rejected() -> None:
    original = MODULE.BASELINE.read_text(encoding="utf-8")
    try:
        payload = __import__("json").loads(original)
        payload["findings"].append(payload["findings"][0])
        payload["expected_total"] += 1
        MODULE.BASELINE.write_text(__import__("json").dumps(payload), encoding="utf-8")
        try:
            MODULE.load_baseline()
        except ValueError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("duplicate baseline accepted")
    finally:
        MODULE.BASELINE.write_text(original, encoding="utf-8")


def test_expected_total_mismatch_rejected() -> None:
    original = MODULE.BASELINE.read_text(encoding="utf-8")
    try:
        payload = __import__("json").loads(original)
        payload["expected_total"] += 1
        MODULE.BASELINE.write_text(__import__("json").dumps(payload), encoding="utf-8")
        try:
            MODULE.load_baseline()
        except ValueError as exc:
            assert "expected_total" in str(exc)
        else:
            raise AssertionError("mismatch accepted")
    finally:
        MODULE.BASELINE.write_text(original, encoding="utf-8")


def test_malformed_error_like_output_fails_closed() -> None:
    findings, summary, unparsed = MODULE.parse_output("app/a.py:2: error: malformed\nFound 1 error in 1 file.\n")
    assert findings == []
    assert summary == 1
    assert len(unparsed) == 1

