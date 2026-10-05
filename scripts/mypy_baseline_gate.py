"""Fail when mypy reports diagnostics outside the reviewed repository baseline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = Path(__file__).with_name("mypy_baseline.json")
COMMAND = ["python", "-m", "mypy", "app", "--show-error-codes"]
DIAGNOSTIC_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<column>\d+))?: error: "
    r"(?P<message>.*?)(?:\s+\[(?P<code>[a-zA-Z0-9_-]+)\])?$"
)
SUMMARY_RE = re.compile(r"^Found (?P<count>\d+) errors? in (?P<files>\d+) files? \(checked \d+ source files?\)$")
CONFIG_FINGERPRINT_ALGORITHM = "sha256-text-lf-v1"


class BaselineError(ValueError):
    """Raised when a baseline or mypy output cannot be trusted."""


def _relative_path(value: str, root: Path) -> str:
    normalized = value.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", normalized) and os.name != "nt":
        raise BaselineError(f"cannot bind a Windows absolute path on this platform: {value}")
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            normalized = candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise BaselineError(f"diagnostic path is outside the repository: {value}") from exc
    normalized = normalized.removeprefix("./").strip("/")
    if not normalized or normalized.startswith("../"):
        raise BaselineError(f"diagnostic path is not repository-relative: {value}")
    return normalized


def parse_diagnostics(output: str, root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Parse all error diagnostics; fail closed on unrecognized error lines."""
    findings: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        if ": error:" not in raw_line:
            continue
        match = DIAGNOSTIC_RE.fullmatch(raw_line.strip())
        if match is None:
            raise BaselineError(f"unrecognized mypy diagnostic: {raw_line}")
        code = match.group("code")
        if not code:
            raise BaselineError(f"mypy diagnostic has no error code: {raw_line}")
        column = match.group("column")
        findings.append(
            {
                "path": _relative_path(match.group("path"), root),
                "line": int(match.group("line")),
                "column": int(column) if column else None,
                "error_code": code,
                "message": " ".join(match.group("message").split()),
            }
        )
    return sorted(findings, key=_finding_key)


def _finding_key(finding: dict[str, Any]) -> tuple[str, int, int, str, str]:
    return (
        str(finding["path"]),
        int(finding["line"]),
        int(finding["column"] or 0),
        str(finding["error_code"]),
        str(finding["message"]),
    )


def _identity(finding: dict[str, Any]) -> tuple[str, int, int | None, str, str]:
    return (
        str(finding["path"]),
        int(finding["line"]),
        int(finding["column"]) if finding["column"] is not None else None,
        str(finding["error_code"]),
        str(finding["message"]),
    )


def _identity_key(identity: tuple[str, int, int | None, str, str]) -> tuple[str, int, int, str, str]:
    return (identity[0], identity[1], identity[2] if identity[2] is not None else 0, identity[3], identity[4])


def canonicalize_text_line_endings(data: bytes) -> bytes:
    """Normalize CRLF and lone CR line endings to LF, preserving all other bytes."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def config_fingerprint(data: bytes) -> tuple[str, int]:
    """Return the versioned SHA-256 and byte length of canonical config bytes."""
    canonical = canonicalize_text_line_endings(data)
    return hashlib.sha256(canonical).hexdigest(), len(canonical)


def compare_findings(
    current: list[dict[str, Any]], baseline: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return new, resolved, and unchanged diagnostics using multiset identity."""
    current_by_id = Counter(_identity(item) for item in current)
    baseline_by_id = Counter(_identity(item) for item in baseline)
    index = {_identity(item): item for item in current + baseline}

    def expand(delta: Counter[tuple[str, int, int | None, str, str]]) -> list[dict[str, Any]]:
        return [index[key] for key in sorted(delta, key=_identity_key) for _ in range(delta[key])]

    new = current_by_id - baseline_by_id
    resolved = baseline_by_id - current_by_id
    unchanged = current_by_id & baseline_by_id
    return expand(new), expand(resolved), expand(unchanged)


def _load_baseline(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"cannot load mypy baseline {path}: {exc}") from exc
    required = {
        "schema_version",
        "mypy_version",
        "config_fingerprint_algorithm",
        "config_sha256",
        "config_canonical_bytes",
        "command",
        "originating_commit",
        "finding_count",
        "file_count",
        "findings",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise BaselineError("baseline fields do not match the required schema")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or not isinstance(value["findings"], list):
        raise BaselineError("unsupported baseline schema or findings field")
    for item in value["findings"]:
        if not isinstance(item, dict) or set(item) != {"path", "line", "column", "error_code", "message"}:
            raise BaselineError("baseline contains a malformed finding")
        if (
            not isinstance(item["path"], str)
            or not item["path"]
            or item["path"].startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:", item["path"])
            or ".." in item["path"].replace("\\", "/").split("/")
            or type(item["line"]) is not int
            or item["line"] < 1
            or (item["column"] is not None and (type(item["column"]) is not int or item["column"] < 1))
            or not isinstance(item["error_code"], str)
            or not item["error_code"]
            or not isinstance(item["message"], str)
            or not item["message"]
        ):
            raise BaselineError("baseline contains an invalid finding identity")
    for field in ("mypy_version", "config_fingerprint_algorithm", "config_sha256", "originating_commit"):
        if not isinstance(value[field], str) or not value[field]:
            raise BaselineError(f"baseline {field} must be a non-empty string")
    if value["config_fingerprint_algorithm"] != CONFIG_FINGERPRINT_ALGORITHM:
        raise BaselineError("unsupported config fingerprint algorithm")
    if type(value["config_canonical_bytes"]) is not int or value["config_canonical_bytes"] < 0:
        raise BaselineError("baseline config_canonical_bytes must be a non-negative integer")
    if not isinstance(value["command"], list) or any(not isinstance(arg, str) for arg in value["command"]):
        raise BaselineError("baseline command must be a list of strings")
    for field in ("finding_count", "file_count"):
        if type(value[field]) is not int or value[field] < 0:
            raise BaselineError(f"baseline {field} must be a non-negative integer")
    if value["findings"] != sorted(value["findings"], key=_finding_key):
        raise BaselineError("baseline findings are not deterministically sorted")
    return value


def _validate_metadata(baseline: dict[str, Any], root: Path) -> None:
    actual_version = importlib.metadata.version("mypy")
    actual_config_hash, actual_config_bytes = config_fingerprint((root / "pyproject.toml").read_bytes())
    expected = {
        "mypy_version": actual_version,
        "config_fingerprint_algorithm": CONFIG_FINGERPRINT_ALGORITHM,
        "config_sha256": actual_config_hash,
        "config_canonical_bytes": actual_config_bytes,
        "command": COMMAND,
        "originating_commit": "ad9bb4e58618aa340b273bc2d7aa6f5763cb3d24",
    }
    for field, actual in expected.items():
        if baseline.get(field) != actual:
            raise BaselineError(f"baseline {field} mismatch: expected {actual!r}, got {baseline.get(field)!r}")
    findings = baseline["findings"]
    if baseline["finding_count"] != len(findings):
        raise BaselineError("baseline finding_count does not match findings")
    file_count = len({item["path"] for item in findings})
    if baseline["file_count"] != file_count:
        raise BaselineError("baseline file_count does not match findings")


def run_gate(baseline_path: Path = DEFAULT_BASELINE, root: Path = REPO_ROOT) -> int:
    baseline = _load_baseline(baseline_path)
    _validate_metadata(baseline, root)
    process = subprocess.run(
        [sys.executable, "-m", "mypy", "app", "--show-error-codes"],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    try:
        current = parse_diagnostics(process.stdout, root)
    except BaselineError as exc:
        print(f"MYPY_BASELINE_GATE_ERROR: {exc}", file=sys.stderr)
        return 2
    summaries = [SUMMARY_RE.fullmatch(line.strip()) for line in process.stdout.splitlines()]
    summary = next((match for match in summaries if match is not None), None)
    if process.returncode not in (0, 1) or (process.returncode == 1 and not current):
        print(f"MYPY_EXECUTION_FAILED: exit={process.returncode}", file=sys.stderr)
        return 2
    if summary and int(summary.group("count")) != len(current):
        print("MYPY_BASELINE_GATE_ERROR: summary count differs from parsed diagnostics", file=sys.stderr)
        return 2
    current_file_count = len({item["path"] for item in current})
    if summary and int(summary.group("files")) != current_file_count:
        print("MYPY_BASELINE_GATE_ERROR: summary file count differs from parsed diagnostics", file=sys.stderr)
        return 2
    if not summary and current:
        print("MYPY_BASELINE_GATE_ERROR: diagnostics present without a recognized summary", file=sys.stderr)
        return 2

    new, resolved, unchanged = compare_findings(current, baseline["findings"])
    print(
        f"MYPY_BASELINE={len(baseline['findings'])} CURRENT={len(current)} "
        f"NEW={len(new)} RESOLVED={len(resolved)} UNCHANGED={len(unchanged)}"
    )
    if new:
        print("New mypy diagnostics:")
        for item in new:
            print(f"  {item['path']}:{item['line']}:{item['column'] or 0}: [{item['error_code']}] {item['message']}")
        return 1
    if resolved:
        print("Resolved mypy diagnostics (baseline intentionally unchanged):")
        for item in resolved:
            print(f"  {item['path']}:{item['line']}:{item['column'] or 0}: [{item['error_code']}] {item['message']}")
    if process.returncode == 1 and not resolved:
        print("Existing mypy debt remains; no new diagnostics.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        return run_gate(args.baseline.resolve(), REPO_ROOT)
    except (BaselineError, importlib.metadata.PackageNotFoundError) as exc:
        print(f"MYPY_BASELINE_GATE_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
