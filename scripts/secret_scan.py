"""Fail when tracked files contain obvious, non-placeholder credentials."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ASSIGNMENT = re.compile(
    r"\b(?:TELEGRAM_BOT_TOKEN|GEMINI_API_KEY|JWT_SECRET|PAYMENT_WEBHOOK_SECRET|"
    r"TELEGRAM_WEBHOOK_SECRET|PAYMENT_PROVIDER_API_KEY)\s*=\s*([^\s#]+)"
)
TELEGRAM_TOKEN = re.compile(r"\b\d{8,}:[A-Za-z0-9_-]{20,}\b")
PLACEHOLDER_PARTS = ("replace-with", "your-", "example", "changeme")


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True, text=False
    ).stdout.decode().split("\0")
    findings: list[str] = []
    for filename in filter(None, files):
        if filename == ".env" or filename.startswith(".env.") and filename != ".env.example":
            continue
        try:
            content = Path(filename).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            assignment = ASSIGNMENT.search(line)
            if assignment:
                value = assignment.group(1).strip('"\'')
                if value and not any(part in value.lower() for part in PLACEHOLDER_PARTS):
                    findings.append(f"{filename}:{line_number}: credential assignment")
            if TELEGRAM_TOKEN.search(line):
                findings.append(f"{filename}:{line_number}: Telegram token pattern")
    if findings:
        print("Potential credentials found in tracked files:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
