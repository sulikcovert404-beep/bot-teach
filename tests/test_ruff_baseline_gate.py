from pathlib import Path

from scripts.ruff_baseline_gate import compare_findings


def _finding(path: Path, code: str, row: int = 1) -> dict[str, object]:
    return {
        "filename": str(path),
        "code": code,
        "message": "representative Ruff finding",
        "location": {"row": row, "column": 8},
        "end_location": {"row": row, "column": 14},
    }


def test_line_movement_keeps_existing_finding(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    current_root = tmp_path / "current"
    baseline_root.mkdir()
    current_root.mkdir()
    baseline_file = baseline_root / "sample.py"
    current_file = current_root / "sample.py"
    baseline_file.write_text("item = dict()\n", encoding="utf-8")
    current_file.write_text("\nitem = dict()\n", encoding="utf-8")

    result = compare_findings(
        [_finding(baseline_file, "C408")],
        [_finding(current_file, "C408", row=2)],
        baseline_root,
        current_root,
    )

    assert result[:3] == (1, 0, 0)


def test_new_duplicate_finding_is_rejected(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    current_root = tmp_path / "current"
    baseline_root.mkdir()
    current_root.mkdir()
    baseline_file = baseline_root / "sample.py"
    current_file = current_root / "sample.py"
    baseline_file.write_text("item = dict()\n", encoding="utf-8")
    current_file.write_text("item = dict()\nother = dict()\n", encoding="utf-8")
    baseline_finding = _finding(baseline_file, "C408")
    current_findings = [baseline_finding.copy(), _finding(current_file, "C408", row=2)]
    current_findings[0]["filename"] = str(current_file)

    result = compare_findings(
        [baseline_finding], current_findings, baseline_root, current_root
    )

    assert result[0:3] == (1, 1, 0)


def test_changed_import_block_preserves_baseline_ordinal(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    current_root = tmp_path / "current"
    baseline_root.mkdir()
    current_root.mkdir()
    baseline_file = baseline_root / "sample.py"
    current_file = current_root / "sample.py"
    baseline_file.write_text("import z\nimport a\n", encoding="utf-8")
    current_file.write_text("import c\nimport b\n", encoding="utf-8")

    result = compare_findings(
        [_finding(baseline_file, "I001")],
        [_finding(current_file, "I001", row=2)],
        baseline_root,
        current_root,
    )

    assert result[:3] == (1, 0, 0)
