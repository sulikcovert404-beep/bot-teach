from __future__ import annotations

import hashlib
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts import mypy_baseline_gate
from scripts.mypy_baseline_gate import BaselineError, compare_findings, parse_diagnostics

ROOT = Path(__file__).resolve().parents[1]


def finding(path: str, line: int, code: str, message: str, column: int | None = None) -> dict[str, object]:
    return {
        "path": path,
        "line": line,
        "column": column,
        "error_code": code,
        "message": message,
    }


def test_exact_baseline_matches() -> None:
    baseline = [finding("app/a.py", 10, "arg-type", "bad argument")]
    new, resolved, unchanged = compare_findings(baseline, baseline)
    assert (new, resolved, unchanged) == ([], [], baseline)


def test_added_diagnostic_fails_by_identity() -> None:
    baseline = [finding("app/a.py", 10, "arg-type", "bad argument")]
    current = baseline + [finding("app/b.py", 20, "return-value", "bad return")]
    new, resolved, _ = compare_findings(current, baseline)
    assert new == [finding("app/b.py", 20, "return-value", "bad return")]
    assert resolved == []


def test_removed_diagnostic_is_reported_as_improvement() -> None:
    baseline = [finding("app/a.py", 10, "arg-type", "bad argument")]
    new, resolved, unchanged = compare_findings([], baseline)
    assert new == []
    assert resolved == baseline
    assert unchanged == []


def test_replacement_with_same_count_still_fails() -> None:
    baseline = [finding("app/a.py", 10, "arg-type", "bad argument")]
    current = [finding("app/a.py", 10, "return-value", "different error")]
    new, resolved, unchanged = compare_findings(current, baseline)
    assert len(current) == len(baseline)
    assert len(new) == 1
    assert resolved == baseline
    assert unchanged == []


@pytest.mark.parametrize(
    "changed",
    [
        finding("app/other.py", 10, "arg-type", "bad argument"),
        finding("app/a.py", 11, "arg-type", "bad argument"),
        finding("app/a.py", 10, "return-value", "bad argument"),
        finding("app/a.py", 10, "arg-type", "different message"),
    ],
)
def test_path_line_code_or_message_change_is_new_and_resolved(changed: dict[str, object]) -> None:
    baseline = [finding("app/a.py", 10, "arg-type", "bad argument")]
    new, resolved, _ = compare_findings([changed], baseline)
    assert new == [changed]
    assert resolved == baseline


def test_duplicate_diagnostics_use_deterministic_multiset_matching() -> None:
    duplicate = finding("app/a.py", 10, "arg-type", "bad argument")
    new, resolved, unchanged = compare_findings([duplicate, duplicate], [duplicate])
    assert new == [duplicate]
    assert resolved == []
    assert unchanged == [duplicate]


def test_parser_normalizes_windows_separators_and_requires_codes() -> None:
    result = parse_diagnostics(
        r"app\a.py:10: error: bad argument  [arg-type]",
        root=ROOT,
    )
    assert result == [finding("app/a.py", 10, "arg-type", "bad argument")]


def test_parser_rejects_unbound_windows_absolute_paths() -> None:
    with pytest.raises(BaselineError, match="outside the repository|Windows absolute"):
        parse_diagnostics(r"C:\outside\app\a.py:10: error: bad argument [arg-type]", root=ROOT)


def test_parser_fails_closed_on_unknown_diagnostic_format() -> None:
    with pytest.raises(BaselineError, match="unrecognized"):
        parse_diagnostics("app/a.py: error: bad argument [arg-type]")


def test_parser_fails_closed_when_error_code_missing() -> None:
    with pytest.raises(BaselineError, match="no error code"):
        parse_diagnostics("app/a.py:10: error: bad argument")


def test_baseline_file_is_deterministic_json() -> None:
    baseline_path = ROOT / "scripts" / "mypy_baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert baseline["finding_count"] == len(baseline["findings"])
    assert baseline["file_count"] == len({item["path"] for item in baseline["findings"]})


def test_malformed_baseline_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"errors": 568}), encoding="utf-8")
    with pytest.raises(BaselineError, match="fields"):
        mypy_baseline_gate._load_baseline(path)


def test_mypy_execution_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mypy_baseline_gate.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 2, "fatal mypy failure\n", None),
    )
    assert mypy_baseline_gate.run_gate(root=ROOT) == 2


def _write_tiny_baseline(root: Path, path: Path, items: list[dict[str, object]]) -> None:
    config = root / "pyproject.toml"
    config.write_text("[tool.mypy]\nstrict = true\n", encoding="utf-8")
    payload = {
        "schema_version": 1,
        "mypy_version": "1.20.2",
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "command": mypy_baseline_gate.COMMAND,
        "originating_commit": "ad9bb4e58618aa340b273bc2d7aa6f5763cb3d24",
        "finding_count": len(items),
        "file_count": len({item["path"] for item in items}),
        "findings": items,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_gate_fails_for_new_diagnostic_even_when_count_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_finding = finding("app/a.py", 10, "arg-type", "bad argument")
    _write_tiny_baseline(tmp_path, baseline_path, [baseline_finding])
    monkeypatch.setattr(mypy_baseline_gate.importlib.metadata, "version", lambda _: "1.20.2")
    monkeypatch.setattr(
        mypy_baseline_gate.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(
            args[0],
            1,
            "app/a.py:10: error: different error [return-value]\nFound 1 error in 1 file (checked 2 source files)\n",
            None,
        ),
    )
    assert mypy_baseline_gate.run_gate(baseline_path, tmp_path) == 1


def test_gate_reports_resolved_diagnostic_without_rewriting_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline_path = tmp_path / "baseline.json"
    _write_tiny_baseline(tmp_path, baseline_path, [finding("app/a.py", 10, "arg-type", "bad argument")])
    original_bytes = baseline_path.read_bytes()
    monkeypatch.setattr(mypy_baseline_gate.importlib.metadata, "version", lambda _: "1.20.2")
    monkeypatch.setattr(
        mypy_baseline_gate.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, "Success: no issues found in 2 source files\n", None),
    )
    assert mypy_baseline_gate.run_gate(baseline_path, tmp_path) == 0
    assert "RESOLVED=1" in capsys.readouterr().out
    assert baseline_path.read_bytes() == original_bytes
