"""Fail CI only when the current Ruff run adds findings over its base revision."""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUFF_PATHS = ("app", "tests", "migrations", "scripts")
ARCHIVE_PATHS = (".gitignore", "pyproject.toml", *RUFF_PATHS)


def _git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _run_ruff(root: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", *RUFF_PATHS, "--output-format=json"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Ruff could not complete: {result.stderr.strip()}")
    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ruff returned invalid JSON output") from exc
    if not isinstance(findings, list):
        raise TypeError("Ruff returned an unexpected JSON document")
    return findings


def _relative_path(filename: str, root: Path) -> str:
    path = Path(filename).resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"Ruff returned a path outside the checkout: {filename}") from exc


def _source_span(finding: dict[str, Any], root: Path) -> str:
    path = root / _relative_path(finding["filename"], root)
    lines = path.read_text(encoding="utf-8").splitlines()
    start = finding["location"]
    end = finding["end_location"]
    if start["row"] < 1 or end["row"] > len(lines):
        raise RuntimeError(f"Ruff returned an invalid location for {path}")
    if start["row"] == end["row"]:
        selected = [lines[start["row"] - 1][start["column"] - 1 : end["column"] - 1]]
    else:
        selected = lines[start["row"] - 1 : end["row"]]
        selected[0] = selected[0][start["column"] - 1 :]
        selected[-1] = selected[-1][: end["column"] - 1]
    return re.sub(r"\s+", " ", " ".join(selected)).strip()


def fingerprints(findings: list[dict[str, Any]], root: Path) -> Counter[tuple[str, ...]]:
    """Build stable finding identities independent of line-number movement."""
    keyed: list[tuple[str, str, str, str]] = []
    for finding in findings:
        path = _relative_path(finding["filename"], root)
        code = finding["code"]
        message = finding["message"]
        span = "import-block" if code == "I001" else _source_span(finding, root)
        keyed.append((path, code, message, span))

    # Import-sort findings cover the entire block, whose text changes when a
    # nearby import is added or moved. Ordinal identity preserves the existing
    # block while still detecting an additional malformed block in that file.
    counts: Counter[tuple[str, str, str]] = Counter()
    result: Counter[tuple[str, ...]] = Counter()
    for path, code, message, span in sorted(keyed):
        if code == "I001":
            key = (path, code, message)
            result[(*key, f"block-{counts[key]}")] += 1
            counts[key] += 1
        else:
            result[(path, code, message, span)] += 1
    return result


def compare_findings(
    baseline: list[dict[str, Any]], current: list[dict[str, Any]], baseline_root: Path, current_root: Path
) -> tuple[int, int, int, Counter[tuple[str, ...]]]:
    base = fingerprints(baseline, baseline_root)
    head = fingerprints(current, current_root)
    new = head - base
    resolved = base - head
    pre_existing = sum(head.values()) - sum(new.values())
    return pre_existing, sum(new.values()), sum(resolved.values()), new


def _extract_baseline(base_ref: str, destination: Path) -> str:
    base_sha = _git_output("rev-parse", "--verify", f"{base_ref}^{{commit}}")
    archive = subprocess.run(
        ["git", "archive", "--format=tar", base_sha, *ARCHIVE_PATHS],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        tar.extractall(destination, filter="data")
    return base_sha


def main() -> int:
    base_ref = os.environ.get("RUFF_BASE_REF") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not base_ref:
        print("RUFF_BASE_REF or a base commit argument is required", file=sys.stderr)
        return 2
    head_sha = _git_output("rev-parse", "HEAD")
    try:
        with tempfile.TemporaryDirectory(prefix="ruff-baseline-") as temporary:
            baseline_root = Path(temporary)
            base_sha = _extract_baseline(base_ref, baseline_root)
            baseline = _run_ruff(baseline_root)
            current = _run_ruff(ROOT)
            pre_existing, new_count, resolved, new = compare_findings(
                baseline, current, baseline_root, ROOT
            )
    except (OSError, RuntimeError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Ruff baseline comparison failed closed: {exc}", file=sys.stderr)
        return 2

    print(f"Ruff baseline: {base_sha}")
    print(f"Candidate: {head_sha}")
    print(f"PRE_EXISTING={pre_existing} NEW={new_count} RESOLVED={resolved}")
    if new:
        for finding, count in sorted(new.items()):
            print(f"NEW x{count}: {finding[0]} {finding[1]} {finding[2]} [{finding[3]}]")
        return 1
    print("Ruff baseline gate: PASS (no new findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
