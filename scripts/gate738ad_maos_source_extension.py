"""Fail-closed additive source binding for the MAOS kernel image sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

BASE_MANIFEST_PATH = "docs/GATE738AD_CANDIDATE_MANIFEST.json"
EXTENSION_PATH = "docs/GATE738AD_MAOS_KERNEL_V1_SOURCE_EXTENSION.json"
BASE_MANIFEST_SHA256 = "17d8f9ef3a89631f8608ab46712554f1c0109723c1ab7cc25de50c15ff1ad8b6"
BASE_MANIFEST_GIT_BLOB = "8d54d63d9332d6872a51d1ba652d1d266de523eb"
PURPOSE = "MAOS_KERNEL_V1"

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

_EXTENSION_KEYS = {
    "schema_version",
    "purpose",
    "base_manifest_path",
    "base_manifest_sha256",
    "base_manifest_git_blob",
    "files",
}
_FILE_KEYS = {"path", "git_blob", "sha256", "size_bytes"}


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


def verify_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
) -> set[str]:
    """Validate frozen base identity and the complete MAOS-only extension."""
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
    _require(extension["purpose"] == PURPOSE, "source extension purpose mismatch")
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
        _require(path.startswith("app/maos/"), f"extension path outside MAOS app namespace: {path}")
        _require(path.endswith(".py"), f"unsupported MAOS source type: {path}")
        _require(path not in extension_paths, f"duplicate/conflicting extension path: {path}")
        _require(path not in base_paths, f"extension conflicts with frozen base path: {path}")
        _require(type(item["size_bytes"]) is int, f"invalid byte size for {path}")
        _require(item["size_bytes"] == len(content), f"source size mismatch: {path}")
        _require(item["sha256"] == _sha256(content), f"source SHA256 mismatch: {path}")
        _require(item["git_blob"] == _git_blob_oid(content), f"source Git blob mismatch: {path}")
        extension_paths.add(path)

    _require(
        extension_paths == EXPECTED_MAOS_PATHS,
        "MAOS extension is incomplete or contains unapproved paths",
    )
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    _require(
        "COPY app ./app" in dockerfile,
        "Dockerfile no longer exposes MAOS extension paths through the approved app COPY",
    )
    return base_paths | extension_paths


def load_effective_candidate_paths(root: Path) -> set[str]:
    """Load the immutable Gate738AD base plus its fail-closed MAOS extension."""
    base_path = root / BASE_MANIFEST_PATH
    extension_path = root / EXTENSION_PATH
    _require(base_path.is_file(), "frozen Gate738AD base manifest is missing")
    _require(extension_path.is_file(), "MAOS source extension metadata is missing")
    try:
        extension = json.loads(extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS source extension is not valid JSON") from exc
    return verify_source_extension(root, base_path.read_bytes(), extension)
