#!/usr/bin/env python3
"""Prepare an encrypted, checksum-verified offsite backup package locally.

This tool intentionally has no network or object-storage code.  It is the
local preparation half of the R2 workflow: validate a completed PostgreSQL
run, create deterministic metadata, compress, encrypt, and verify artifacts.
Production execution and upload are separate Commander gates.
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

_SAFE_DATABASE = re.compile(r"^[A-Za-z0-9_-]+$")


class PackageError(RuntimeError):
    """Raised when a local package cannot be prepared safely."""


@dataclass(frozen=True)
class PackagePlan:
    database: str
    timestamp_utc: str
    source_dump: Path
    output_dir: Path

    @property
    def prefix(self) -> Path:
        dt = datetime.fromisoformat(self.timestamp_utc)
        return (
            self.output_dir
            / "ai-teacher"
            / "postgresql"
            / self.database
            / "v1"
            / dt.strftime("%Y/%m/%d")
            / dt.strftime("%Y%m%dT%H%M%SZ")
        )

    @property
    def compressed(self) -> Path:
        return self.prefix / f"{self.database}.dump.zst"

    @property
    def encrypted(self) -> Path:
        return self.prefix / f"{self.database}.dump.zst.age"

    @property
    def manifest(self) -> Path:
        return self.prefix / f"{self.database}.manifest.json"

    @property
    def sha256(self) -> Path:
        return self.prefix / f"{self.database}.sha256"

    @property
    def complete(self) -> Path:
        return self.prefix / "COMPLETE"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: dict[str, object]) -> bytes:
    """Return deterministic UTF-8 JSON with one trailing newline."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def build_manifest(
    plan: PackagePlan,
    *,
    postgres_version: str = "unknown",
    tool_version: str = "r2-offsite-packager-v1",
) -> dict[str, object]:
    if not _SAFE_DATABASE.fullmatch(plan.database):
        raise PackageError(f"unsafe database name: {plan.database!r}")
    if plan.source_dump.is_symlink() or not plan.source_dump.is_file():
        raise PackageError(f"source dump does not exist: {plan.source_dump}")
    return {
        "schema_version": 1,
        "project": "ai-teacher",
        "database": plan.database,
        "timestamp_utc": plan.timestamp_utc,
        "postgres_version": postgres_version,
        "dump_format": "postgres-custom",
        "compression": "zstd",
        "encryption": "age",
        "plaintext_size_bytes": plan.source_dump.stat().st_size,
        "plaintext_sha256": sha256_file(plan.source_dump),
        "object_key": (
            f"ai-teacher/postgresql/{plan.database}/v1/"
            f"{plan.prefix.parent.name}/{plan.prefix.name}/"
            f"{plan.encrypted.name}"
        ),
        "tool_version": tool_version,
        "source_local_run": str(plan.source_dump.parent),
    }


def _run(command: Sequence[str]) -> None:
    try:
        subprocess.run(tuple(command), check=True, capture_output=True, timeout=3600)
    except FileNotFoundError as exc:
        raise PackageError(f"required local tool is unavailable: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise PackageError(f"local packaging command failed: {command[0]}") from exc


def prepare_package(plan: PackagePlan, *, recipient: str | None, execute: bool) -> dict[str, object]:
    manifest = build_manifest(plan)
    if not execute:
        return {
            "status": "dry_run",
            "database": plan.database,
            "prefix": str(plan.prefix),
            "objects": [plan.compressed.name, plan.encrypted.name, plan.manifest.name, plan.sha256.name, "COMPLETE"],
            "manifest_sha256": hashlib.sha256(canonical_json(manifest)).hexdigest(),
        }
    if not recipient:
        raise PackageError("--recipient is required with --execute")
    if shutil.which("zstd") is None or shutil.which("age") is None:
        raise PackageError("zstd and age must be installed for local execution")

    if plan.source_dump.is_symlink() or not plan.source_dump.is_file():
        raise PackageError(f"source dump does not exist: {plan.source_dump}")
    if plan.source_dump.stat().st_mode & 0o077:
        raise PackageError(f"source dump is too permissive: {plan.source_dump}")
    plan.prefix.mkdir(mode=0o700, parents=True, exist_ok=False)
    compressed_partial = Path(f"{plan.compressed}.partial")
    encrypted_partial = Path(f"{plan.encrypted}.partial")
    try:
        _run(("zstd", "--quiet", "--force", str(plan.source_dump), "-o", str(compressed_partial)))
        compressed_partial.replace(plan.compressed)
        plan.compressed.chmod(0o600)
        _run(("age", "-r", recipient, "-o", str(encrypted_partial), str(plan.compressed)))
        encrypted_partial.replace(plan.encrypted)
        plan.encrypted.chmod(0o600)
        manifest["compressed_size_bytes"] = plan.compressed.stat().st_size
        manifest["encrypted_size_bytes"] = plan.encrypted.stat().st_size
        manifest["ciphertext_sha256"] = sha256_file(plan.encrypted)
        plan.manifest.write_bytes(canonical_json(manifest))
        plan.manifest.chmod(0o600)
        plan.sha256.write_text(f"{manifest['ciphertext_sha256']}  {plan.encrypted.name}\n", encoding="ascii")
        plan.sha256.chmod(0o600)
        plan.complete.write_text("complete\n", encoding="ascii")
        plan.complete.chmod(0o600)
        return {"status": "executed", "database": plan.database, "prefix": str(plan.prefix), "manifest": manifest}
    finally:
        compressed_partial.unlink(missing_ok=True)
        encrypted_partial.unlink(missing_ok=True)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-dump", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timestamp-utc", default=None)
    parser.add_argument("--recipient", help="age recipient; never a private key")
    parser.add_argument("--execute", action="store_true", help="write local package; no upload")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    timestamp = args.timestamp_utc or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = prepare_package(
        PackagePlan(args.database, timestamp, args.source_dump, args.output_dir),
        recipient=args.recipient,
        execute=args.execute,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
