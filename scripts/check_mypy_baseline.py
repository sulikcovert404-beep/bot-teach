"""Run mypy and enforce an exact, reviewable finding-set baseline."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "mypy_baseline.json"
ERROR_RE = re.compile(
    r"^(?P<path>[^:\r\n]+):(?P<line>\d+)(?::(?P<column>\d+))?: error: "
    r"(?P<message>.*?) \[(?P<code>[^\]]+)\]\s*$"
)
SUMMARY_RE = re.compile(r"^Found (?P<count>\d+) errors? in (?P<files>\d+) files?(?:.*)?$")

Finding = tuple[str, int, int, str, str]


def _finding_from_match(match: re.Match[str]) -> Finding:
    return (
        match.group("path").replace("\\", "/"),
        int(match.group("line")),
        int(match.group("column") or 0),
        match.group("code"),
        match.group("message").strip(),
    )


def parse_output(output: str) -> tuple[list[Finding], int | None, list[str]]:
    findings: list[Finding] = []
    unparsed_error_like: list[str] = []
    summary_count: int | None = None
    for line in output.splitlines():
        match = ERROR_RE.match(line)
        if match:
            findings.append(_finding_from_match(match))
            continue
        summary = SUMMARY_RE.match(line.strip())
        if summary:
            summary_count = int(summary.group("count"))
            continue
        if ": error:" in line:
            unparsed_error_like.append(line)
    return findings, summary_count, unparsed_error_like


def load_baseline() -> list[Finding]:
    payload: Any = json.loads(BASELINE.read_text(encoding="utf-8"))
    required = {"schema_version", "baseline_commit", "command", "expected_total", "fingerprint", "findings"}
    if set(payload) != required or payload["fingerprint"] != ["path", "line", "column", "code", "message"]:
        raise ValueError("invalid baseline schema")
    findings = [
        (str(item["path"]), int(item["line"]), int(item["column"]), str(item["code"]), str(item["message"]))
        for item in payload["findings"]
    ]
    if payload["expected_total"] != len(findings):
        raise ValueError("baseline expected_total mismatch")
    if len(set(findings)) != len(findings):
        raise ValueError("duplicate baseline finding")
    return findings


def compare(current: list[Finding], baseline: list[Finding]) -> tuple[set[Finding], set[Finding], int]:
    current_counts = Counter(current)
    baseline_counts = Counter(baseline)
    duplicates = sum(count - 1 for count in current_counts.values() if count > 1)
    return set(current_counts) - set(baseline_counts), set(baseline_counts) - set(current_counts), duplicates


def main() -> int:
    try:
        baseline = load_baseline()
        proc = subprocess.run(
            [sys.executable, "-m", "mypy", "app"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        output = proc.stdout + proc.stderr
        findings, summary_count, unparsed = parse_output(output)
        print(output, end="")
        new, resolved, duplicates = compare(findings, baseline)
        print(f"mypy raw findings: {len(findings)}")
        print(f"baseline findings: {len(baseline)}")
        print(f"new findings: {len(new)}")
        print(f"resolved baseline findings: {len(resolved)}")
        print(f"duplicate current findings: {duplicates}")
        if proc.returncode not in (0, 1):
            print("result: FAIL (mypy execution/config failure)")
            return 1
        if summary_count is None or summary_count != len(findings) or unparsed:
            print("result: FAIL (unexpected or unparseable mypy output)")
            return 1
        if new or resolved or duplicates:
            print("result: FAIL")
            return 1
        print("result: PASS")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"result: FAIL CLOSED ({exc})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
