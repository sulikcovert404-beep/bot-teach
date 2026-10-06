"""Fail-closed additive source binding for the MAOS kernel image sources."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

BASE_MANIFEST_PATH = "docs/GATE738AD_CANDIDATE_MANIFEST.json"
EXTENSION_PATH = "docs/GATE738AD_MAOS_KERNEL_V1_SOURCE_EXTENSION.json"
AUTHORITY_EXTENSION_PATH = "docs/GATE738AD_MAOS_AUTHORITY_V1_SOURCE_EXTENSION.json"
A10_EXTENSION_PATH = "docs/GATE738AD_MAOS_A10_PERSISTENCE_SOURCE_EXTENSION.json"
SUCCESSOR_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A10P.json"
BASE_MANIFEST_SHA256 = "17d8f9ef3a89631f8608ab46712554f1c0109723c1ab7cc25de50c15ff1ad8b6"
BASE_MANIFEST_GIT_BLOB = "8d54d63d9332d6872a51d1ba652d1d266de523eb"
PURPOSE = "MAOS_KERNEL_V1"
AUTHORITY_PURPOSE = "MAOS_AUTHORITY_V1"
A10_PURPOSE = "MAOS_A10_PERSISTENCE_V1"
SUCCESSOR_BASELINE_PURPOSE = "GATE738AD_SUCCESSOR_CANDIDATE_V1"

EXPECTED_MAOS_PATHS = frozenset(
    {
        "app/maos/__init__.py",
        "app/maos/kernel_v1/__init__.py",
        "app/maos/kernel_v1/agents.py",
        "app/maos/kernel_v1/authority.py",
        "app/maos/kernel_v1/contracts.py",
        "app/maos/kernel_v1/evidence.py",
        "app/maos/kernel_v1/failure.py",
        "app/maos/kernel_v1/identity.py",
        "app/maos/kernel_v1/lifecycle.py",
        "app/maos/kernel_v1/models.py",
        "app/maos/kernel_v1/ports.py",
        "app/maos/kernel_v1/risk.py",
        "app/maos/kernel_v1/tenant.py",
    }
)
EXPECTED_AUTHORITY_PATHS = frozenset(
    {
        "app/maos/authority_v1/__init__.py",
        "app/maos/authority_v1/contracts.py",
        "app/maos/authority_v1/operation.py",
    }
)
EXPECTED_A10_PATHS = frozenset(
    {"migrations/versions/20261006_0034_maos_durable_foundation.py"}
)

_EXTENSION_KEYS = {
    "schema_version",
    "purpose",
    "base_manifest_path",
    "base_manifest_sha256",
    "base_manifest_git_blob",
    "files",
}
_FILE_KEYS = {"path", "git_blob", "sha256", "size_bytes"}
_SUCCESSOR_KEYS = {
    "schema_version",
    "purpose",
    "predecessor_manifest",
    "additive_provenance",
    "candidate_file_count",
    "candidate_files",
}
_SUCCESSOR_LINEAGE_KEYS = {"path", "purpose", "sha256", "git_blob", "size_bytes"}


class SourceExtensionError(ValueError):
    """Raised when source-closure evidence is missing, ambiguous, or invalid."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceExtensionError(message)


def _relative_file(root: Path, path: Any) -> tuple[str, bytes]:
    _require(isinstance(path, str) and bool(path), "source path must be a non-empty string")
    _require("\\" not in path, f"source path is not canonical POSIX form: {path!r}")
    relative = PurePosixPath(path)
    _require(
        not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == path,
        f"source path is unsafe or non-canonical: {path!r}",
    )
    target = root.joinpath(*relative.parts)
    _require(
        target.is_file() and not target.is_symlink(),
        f"bound source is missing, not a regular file, or a symlink: {path}",
    )
    return path, target.read_bytes()


def _canonical_git_blob(root: Path, path: str) -> tuple[str, bytes]:
    """Read the exact committed blob bytes used as canonical source identity."""
    spec = f"HEAD:{path}"
    try:
        oid = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", spec],
            check=True,
            capture_output=True,
            text=True,
            encoding="ascii",
        ).stdout.strip()
        content = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", oid],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SourceExtensionError(f"canonical Git blob is unavailable: {path}") from exc
    _require(len(oid) == 40 and all(char in "0123456789abcdef" for char in oid),
             f"invalid canonical Git blob identity: {path}")
    _require(_git_blob_oid(content) == oid, f"canonical Git blob bytes mismatch: {path}")
    return oid, content


def verify_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
) -> set[str]:
    """Validate frozen base identity and the complete MAOS-only extension."""
    return _verify_extension(
        root, base_manifest_bytes, extension, purpose=PURPOSE,
        expected_paths=EXPECTED_MAOS_PATHS, forbidden_paths=frozenset(),
    )


def verify_authority_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    kernel_paths: frozenset[str] = EXPECTED_MAOS_PATHS,
) -> set[str]:
    """Validate the exact Authority V1 extension and its disjointness."""
    return _verify_extension(
        root, base_manifest_bytes, extension, purpose=AUTHORITY_PURPOSE,
        expected_paths=EXPECTED_AUTHORITY_PATHS, forbidden_paths=kernel_paths,
        allowed_prefix="app/maos/", copy_line="COPY app ./app",
    )


def verify_a10_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    prior_paths: frozenset[str],
) -> set[str]:
    """Validate the exact A10 migration extension without widening source scope."""
    return _verify_extension(
        root,
        base_manifest_bytes,
        extension,
        purpose=A10_PURPOSE,
        expected_paths=EXPECTED_A10_PATHS,
        forbidden_paths=prior_paths,
        allowed_prefix="migrations/versions/",
        copy_line="COPY migrations ./migrations",
    )


def _verify_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    *,
    purpose: str,
    expected_paths: frozenset[str],
    forbidden_paths: frozenset[str],
    allowed_prefix: str = "app/maos/",
    copy_line: str = "COPY app ./app",
) -> set[str]:
    """Validate one exact additive source record against the frozen base."""
    _require(
        _sha256(base_manifest_bytes) == BASE_MANIFEST_SHA256,
        "frozen Gate738AD base manifest SHA256 mismatch",
    )
    _require(
        _git_blob_oid(base_manifest_bytes) == BASE_MANIFEST_GIT_BLOB,
        "frozen Gate738AD base manifest Git blob mismatch",
    )
    try:
        base = json.loads(base_manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("base manifest is not valid JSON") from exc
    _require(isinstance(base, dict), "base manifest must be a JSON object")
    base_files = base.get("candidate_files")
    _require(isinstance(base_files, list), "base candidate_files must be a list")
    base_paths: set[str] = set()
    for item in base_files:
        _require(isinstance(item, dict), "base candidate file entry must be an object")
        path = item.get("path")
        _require(isinstance(path, str) and path not in base_paths, "duplicate/invalid base path")
        base_paths.add(path)

    _require(isinstance(extension, dict), "source extension must be a JSON object")
    _require(set(extension) == _EXTENSION_KEYS, "source extension keys do not match schema v1")
    _require(extension["schema_version"] == 1, "unknown source extension schema_version")
    _require(extension["purpose"] == purpose, "source extension purpose mismatch")
    _require(extension["base_manifest_path"] == BASE_MANIFEST_PATH, "base manifest path mismatch")
    _require(extension["base_manifest_sha256"] == BASE_MANIFEST_SHA256, "extension base SHA256 mismatch")
    _require(
        extension["base_manifest_git_blob"] == BASE_MANIFEST_GIT_BLOB,
        "extension base Git blob mismatch",
    )

    entries = extension["files"]
    _require(isinstance(entries, list), "source extension files must be a list")
    extension_paths: set[str] = set()
    for item in entries:
        _require(isinstance(item, dict) and set(item) == _FILE_KEYS, "invalid extension file entry")
        path, content = _relative_file(root, item["path"])
        _require(path not in base_paths, f"extension conflicts with frozen base path: {path}")
        _require(path not in forbidden_paths, f"extension overlaps another source extension: {path}")
        _require(path.startswith(allowed_prefix), f"extension path outside approved namespace: {path}")
        _require(path.endswith(".py"), f"unsupported MAOS source type: {path}")
        _require(path not in extension_paths, f"duplicate/conflicting extension path: {path}")
        _require(type(item["size_bytes"]) is int, f"invalid byte size for {path}")
        _require(item["size_bytes"] == len(content), f"source size mismatch: {path}")
        _require(item["sha256"] == _sha256(content), f"source SHA256 mismatch: {path}")
        _require(item["git_blob"] == _git_blob_oid(content), f"source Git blob mismatch: {path}")
        extension_paths.add(path)

    _require(extension_paths == expected_paths, "source extension is incomplete or contains unapproved paths")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    _require(
        copy_line in dockerfile,
        f"Dockerfile no longer exposes extension paths through approved COPY: {copy_line}",
    )
    return base_paths | extension_paths


def verify_successor_candidate_baseline(
    root: Path,
    expected_paths: set[str],
) -> set[str]:
    """Validate the versioned, complete candidate identity without rewriting history."""
    path = root / SUCCESSOR_BASELINE_PATH
    _require(path.is_file() and not path.is_symlink(), "successor candidate baseline is missing or unsafe")
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("successor candidate baseline is not valid JSON") from exc
    _require(isinstance(baseline, dict), "successor candidate baseline must be a JSON object")
    _require(set(baseline) == _SUCCESSOR_KEYS, "successor candidate baseline keys do not match schema")
    _require(baseline["schema_version"] == 1, "unknown successor candidate baseline schema")
    _require(
        baseline["purpose"] == SUCCESSOR_BASELINE_PURPOSE,
        "successor candidate baseline purpose mismatch",
    )

    predecessor = baseline["predecessor_manifest"]
    _require(isinstance(predecessor, dict), "successor predecessor identity must be an object")
    _require(
        set(predecessor) == {"path", "sha256", "git_blob", "size_bytes"},
        "invalid predecessor identity keys",
    )
    _require(predecessor["path"] == BASE_MANIFEST_PATH, "successor predecessor path mismatch")
    _relative_file(root, BASE_MANIFEST_PATH)
    base_oid, base_bytes = _canonical_git_blob(root, BASE_MANIFEST_PATH)
    _require(predecessor["sha256"] == _sha256(base_bytes), "successor predecessor SHA256 mismatch")
    _require(predecessor["git_blob"] == base_oid, "successor predecessor Git blob mismatch")
    _require(type(predecessor["size_bytes"]) is int, "invalid successor predecessor size")
    _require(predecessor["size_bytes"] == len(base_bytes), "successor predecessor size mismatch")

    provenance = baseline["additive_provenance"]
    _require(isinstance(provenance, list), "successor additive provenance must be a list")
    expected_provenance = (
        (EXTENSION_PATH, PURPOSE),
        (AUTHORITY_EXTENSION_PATH, AUTHORITY_PURPOSE),
        (A10_EXTENSION_PATH, A10_PURPOSE),
    )
    _require(len(provenance) == len(expected_provenance), "successor provenance history is incomplete")
    for item, (expected_path, expected_purpose) in zip(provenance, expected_provenance, strict=True):
        _require(isinstance(item, dict), "successor provenance entry must be an object")
        _require(set(item) == _SUCCESSOR_LINEAGE_KEYS, "invalid successor provenance entry keys")
        _require(item["path"] == expected_path, "successor provenance path/order mismatch")
        _require(item["purpose"] == expected_purpose, "successor provenance purpose mismatch")
        _relative_file(root, item["path"])
        oid, content = _canonical_git_blob(root, item["path"])
        _require(item["sha256"] == _sha256(content), f"successor provenance SHA256 mismatch: {expected_path}")
        _require(item["git_blob"] == oid, f"successor provenance Git blob mismatch: {expected_path}")
        _require(type(item["size_bytes"]) is int, f"invalid successor provenance size: {expected_path}")
        _require(item["size_bytes"] == len(content), f"successor provenance size mismatch: {expected_path}")

    entries = baseline["candidate_files"]
    _require(isinstance(entries, list), "successor candidate_files must be a list")
    _require(type(baseline["candidate_file_count"]) is int, "successor candidate_file_count must be an integer")
    _require(baseline["candidate_file_count"] == len(entries), "successor candidate file count mismatch")
    candidate_paths: set[str] = set()
    previous_path = ""
    for item in entries:
        _require(isinstance(item, dict) and set(item) == _FILE_KEYS, "invalid successor candidate file entry")
        candidate_path, _ = _relative_file(root, item["path"])
        oid, content = _canonical_git_blob(root, candidate_path)
        _require(candidate_path > previous_path, "successor candidate paths must be unique and sorted")
        previous_path = candidate_path
        _require(type(item["size_bytes"]) is int, f"invalid candidate size for {candidate_path}")
        _require(item["size_bytes"] == len(content), f"candidate size mismatch: {candidate_path}")
        _require(item["sha256"] == _sha256(content), f"candidate SHA256 mismatch: {candidate_path}")
        _require(item["git_blob"] == oid, f"candidate Git blob mismatch: {candidate_path}")
        candidate_paths.add(candidate_path)
    _require(candidate_paths == expected_paths, "successor candidate path set differs from qualified provenance closure")
    return candidate_paths


def load_effective_candidate_paths(root: Path) -> set[str]:
    """Validate history and the current, complete successor candidate identity."""
    base_path = root / BASE_MANIFEST_PATH
    extension_path = root / EXTENSION_PATH
    authority_extension_path = root / AUTHORITY_EXTENSION_PATH
    a10_extension_path = root / A10_EXTENSION_PATH
    _require(base_path.is_file(), "frozen Gate738AD base manifest is missing")
    _require(extension_path.is_file(), "MAOS source extension metadata is missing")
    _require(authority_extension_path.is_file(), "MAOS Authority source extension metadata is missing")
    _require(a10_extension_path.is_file(), "MAOS A10 source extension metadata is missing")
    try:
        extension = json.loads(extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS source extension is not valid JSON") from exc
    try:
        authority_extension = json.loads(authority_extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS Authority source extension is not valid JSON") from exc
    base_bytes = base_path.read_bytes()
    base = json.loads(base_bytes)
    base_paths = {item["path"] for item in base["candidate_files"]}
    kernel_paths = verify_source_extension(root, base_bytes, extension) - base_paths
    authority_paths = verify_authority_source_extension(
        root, base_bytes, authority_extension, frozenset(kernel_paths)
    )
    try:
        a10_extension = json.loads(a10_extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS A10 source extension is not valid JSON") from exc
    a10_paths = verify_a10_source_extension(
        root, base_bytes, a10_extension, frozenset(kernel_paths | authority_paths)
    )
    effective_paths = base_paths | kernel_paths | authority_paths | a10_paths
    return verify_successor_candidate_baseline(root, effective_paths)
