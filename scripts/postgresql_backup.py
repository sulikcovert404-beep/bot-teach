#!/usr/bin/env python3
"""Create and validate PostgreSQL backups.

The command is deliberately dry-run by default.  Production execution requires
``--execute`` so that an accidental invocation cannot write a dump.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DATABASES = ("education", "mentorbot")
DEFAULT_MIN_FREE_BYTES = 1_000_000_000
_SAFE_DATABASE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class BackupPlan:
    database: str
    dump_path: Path
    manifest_path: Path


def build_plan(output_dir: Path, timestamp: str, databases: Sequence[str]) -> tuple[BackupPlan, ...]:
    for database in databases:
        if not _SAFE_DATABASE.fullmatch(database):
            raise ValueError(f"unsafe database name: {database!r}")
    run_dir = output_dir / timestamp
    return tuple(
        BackupPlan(
            database=database,
            dump_path=run_dir / f"{database}.dump",
            manifest_path=run_dir / f"{database}.manifest.json",
        )
        for database in databases
    )


def ensure_free_space(path: Path, minimum_free_bytes: int) -> None:
    space_path = path
    while not space_path.exists() and space_path != space_path.parent:
        space_path = space_path.parent
    free = shutil.disk_usage(space_path).free
    if free < minimum_free_bytes:
        raise RuntimeError(
            f"insufficient free space: {free} bytes available, "
            f"{minimum_free_bytes} required"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_for(plan: BackupPlan) -> tuple[str, ...]:
    return (
        "pg_dump",
        "--format=custom",
        "--no-owner",
        f"--file={plan.dump_path.as_posix()}.partial",
        plan.database,
    )


def write_manifest(plan: BackupPlan, timestamp: str, postgres_version: str) -> None:
    manifest = {
        "database": plan.database,
        "timestamp_utc": timestamp,
        "postgres_version": postgres_version,
        "size_bytes": plan.dump_path.stat().st_size,
        "sha256": sha256_file(plan.dump_path),
    }
    plan.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_backup(plan: BackupPlan, timestamp: str, *, execute: bool) -> None:
    if not execute:
        print("DRY_RUN", " ".join(command_for(plan)))
        return

    plan.dump_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = Path(f"{plan.dump_path}.partial")
    if partial.exists() or plan.dump_path.exists() or plan.manifest_path.exists():
        raise FileExistsError(f"backup output already exists: {plan.dump_path.parent}")
    try:
        subprocess.run(command_for(plan), check=True, timeout=3600)
        subprocess.run(
            ("pg_restore", "--list", str(partial)),
            check=True,
            timeout=300,
            stdout=subprocess.DEVNULL,
        )
        partial.replace(plan.dump_path)
        plan.dump_path.chmod(0o600)
        write_manifest(plan, timestamp, postgres_version="unknown")
        plan.manifest_path.chmod(0o600)
    finally:
        partial.unlink(missing_ok=True)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("/var/backups/postgresql"))
    parser.add_argument("--database", action="append", dest="databases")
    parser.add_argument("--min-free-bytes", type=int, default=DEFAULT_MIN_FREE_BYTES)
    parser.add_argument("--execute", action="store_true", help="write and validate dumps")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    databases = tuple(args.databases or DEFAULT_DATABASES)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ensure_free_space(args.output_dir, args.min_free_bytes)
    plans = build_plan(args.output_dir, timestamp, databases)
    for plan in plans:
        run_backup(plan, timestamp, execute=args.execute)
    print(json.dumps({"status": "executed" if args.execute else "dry_run", "databases": databases}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
