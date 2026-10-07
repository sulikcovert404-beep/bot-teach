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
A11_EXTENSION_PATH = "docs/GATE738AD_MAOS_A11_LIFECYCLE_SOURCE_EXTENSION.json"
A12F_EXTENSION_PATH = "docs/GATE738AD_MAOS_A12F_PRINCIPAL_SNAPSHOT_SOURCE_EXTENSION.json"
A12TI_EXTENSION_PATH = "docs/GATE738AD_MAOS_A12TI_TENANT_AUTHORITY_SNAPSHOT_SOURCE_EXTENSION.json"
A12TC_EXTENSION_PATH = "docs/GATE738AD_MAOS_A12TC_REQUEST_AUTHORITY_SOURCE_EXTENSION.json"
HISTORICAL_A10_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A10P.json"
HISTORICAL_A11_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A11P.json"
HISTORICAL_A12FP_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A12FP.json"
HISTORICAL_A12TIP_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A12TIP.json"
HISTORICAL_A12FP_SHA256 = "e57de7778266655770d740ec63e74fe6033d98f914a11e04a40349d39eb4d366"
HISTORICAL_A12FP_GIT_BLOB = "beea83b7c14df4e3ac49523e4a9cf84a3c1d6949"
HISTORICAL_A12TIP_SHA256 = "09dd37d2754ac0ebde6f9330cd2def860d7b6ed97689208af82b57ff123d9ed8"
HISTORICAL_A12TIP_GIT_BLOB = "679876ef0dfdba887e67cec6be66406b389ce623"
HISTORICAL_A12TCP_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A12TCP.json"
HISTORICAL_A12TCP_SHA256 = "31b6379d1c5ad78ed85cc544c9cd2ed04ddd096c968d03555b8c43766925c554"
HISTORICAL_A12TCP_GIT_BLOB = "6f4fa7ad95974a88e856995dab0234f4989c1e65"
SUCCESSOR_BASELINE_PATH = "docs/GATE738AD_CANDIDATE_BASELINE_A12TGIQ2.json"
BASE_MANIFEST_SHA256 = "17d8f9ef3a89631f8608ab46712554f1c0109723c1ab7cc25de50c15ff1ad8b6"
BASE_MANIFEST_GIT_BLOB = "8d54d63d9332d6872a51d1ba652d1d266de523eb"
PURPOSE = "MAOS_KERNEL_V1"
AUTHORITY_PURPOSE = "MAOS_AUTHORITY_V1"
A10_PURPOSE = "MAOS_A10_PERSISTENCE_V1"
A11_PURPOSE = "MAOS_A11_LIFECYCLE_V1"
A12F_PURPOSE = "MAOS_A12F_PRINCIPAL_SNAPSHOT_V1"
A12TI_PURPOSE = "MAOS_A12TI_TENANT_AUTHORITY_SNAPSHOT_V1"
A12TC_PURPOSE = "MAOS_A12TC_REQUEST_AUTHORITY_COMPOSITION_V1"
SUCCESSOR_BASELINE_PURPOSE = "GATE738AD_SUCCESSOR_CANDIDATE_A12TGIQ2_V1"
A12TGI_EXTENSION_PATH = "docs/GATE738AD_MAOS_A12TGI_PUBLIC_LEASE_SOURCE_EXTENSION.json"
A12TGI_PURPOSE = "MAOS_A12TGI_PUBLIC_MEMBERSHIP_LEASE_V1"
EXPECTED_A12TGI_PATHS = frozenset({"migrations/versions/20261007_0036_public_membership_lease.py"})

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
EXPECTED_A11_PATHS = frozenset(
    {"migrations/versions/20261006_0035_account_lifecycle_authority.py"}
)
EXPECTED_A12F_PATHS = frozenset({"app/security/authority_snapshot.py"})
EXPECTED_A12TI_PATHS = frozenset({"app/security/tenant_authority_snapshot.py"})
EXPECTED_A12TC_PATHS = frozenset({"app/security/request_authority.py"})

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
    "predecessor_baseline",
    "additive_provenance",
    "candidate_file_count",
    "candidate_files",
}
_SUCCESSOR_LINEAGE_KEYS = {"path", "purpose", "sha256", "git_blob", "size_bytes"}
_PREDECESSOR_KEYS = {"path", "sha256", "git_blob", "size_bytes"}


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


def _canonical_git_blob(root: Path, path: str, *, source: str = "HEAD") -> tuple[str, bytes]:
    """Read canonical committed or staged Git bytes, independent of checkout filters."""
    spec = f":{path}" if source == "index" else f"{source}:{path}"
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


def verify_a11_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    prior_paths: frozenset[str],
) -> set[str]:
    """Validate the exact A11 migration source from canonical staged Git bytes."""
    return _verify_extension(
        root,
        base_manifest_bytes,
        extension,
        purpose=A11_PURPOSE,
        expected_paths=EXPECTED_A11_PATHS,
        forbidden_paths=prior_paths,
        allowed_prefix="migrations/versions/",
        copy_line="COPY migrations ./migrations",
        identity_source="index",
    )


def verify_a12f_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    prior_paths: frozenset[str],
) -> set[str]:
    """Validate the exact A12F runtime source from canonical staged Git bytes."""
    return _verify_extension(
        root,
        base_manifest_bytes,
        extension,
        purpose=A12F_PURPOSE,
        expected_paths=EXPECTED_A12F_PATHS,
        forbidden_paths=prior_paths,
        allowed_prefix="app/security/",
        copy_line="COPY app ./app",
        identity_source="index",
    )


def verify_a12ti_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    prior_paths: frozenset[str],
) -> set[str]:
    """Validate the exact A12TI runtime source from canonical staged Git bytes."""
    return _verify_extension(
        root,
        base_manifest_bytes,
        extension,
        purpose=A12TI_PURPOSE,
        expected_paths=EXPECTED_A12TI_PATHS,
        forbidden_paths=prior_paths,
        allowed_prefix="app/security/",
        copy_line="COPY app ./app",
        identity_source="index",
    )


def verify_a12tc_source_extension(
    root: Path,
    base_manifest_bytes: bytes,
    extension: Any,
    prior_paths: frozenset[str],
) -> set[str]:
    """Validate the exact A12TC runtime source from canonical staged Git bytes."""
    return _verify_extension(
        root,
        base_manifest_bytes,
        extension,
        purpose=A12TC_PURPOSE,
        expected_paths=EXPECTED_A12TC_PATHS,
        forbidden_paths=prior_paths,
        allowed_prefix="app/security/",
        copy_line="COPY app ./app",
        identity_source="index",
    )


def verify_a12tgi_source_extension(
    root: Path, base_manifest_bytes: bytes, extension: Any,
    prior_paths: frozenset[str],
) -> set[str]:
    """Bind the reviewed public lease migration to its canonical index bytes."""
    return _verify_extension(
        root, base_manifest_bytes, extension,
        purpose=A12TGI_PURPOSE, expected_paths=EXPECTED_A12TGI_PATHS,
        forbidden_paths=prior_paths, allowed_prefix="migrations/versions/",
        copy_line="COPY migrations ./migrations", identity_source="index",
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
    identity_source: str | None = None,
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
        path, working_content = _relative_file(root, item["path"])
        if identity_source is None:
            content = working_content
        else:
            oid, content = _canonical_git_blob(root, path, source=identity_source)
            _require(oid == _git_blob_oid(content), f"canonical Git identity mismatch: {path}")
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


def _verify_historical_a12fp_baseline(root: Path) -> tuple[str, bytes]:
    """Bind the predecessor baseline to its immutable, previously qualified bytes."""
    _relative_file(root, HISTORICAL_A12FP_BASELINE_PATH)
    oid, content = _canonical_git_blob(root, HISTORICAL_A12FP_BASELINE_PATH, source="HEAD")
    _require(_sha256(content) == HISTORICAL_A12FP_SHA256, "historical A12FP baseline SHA256 changed")
    _require(oid == HISTORICAL_A12FP_GIT_BLOB, "historical A12FP baseline Git blob changed")
    try:
        historical = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("historical A12FP baseline is not valid JSON") from exc
    _require(isinstance(historical, dict), "historical A12FP baseline must be a JSON object")
    _require(historical.get("candidate_file_count") == 428, "historical A12FP candidate count changed")
    return oid, content


def _verify_historical_a12tip_baseline(root: Path) -> tuple[str, bytes]:
    """Bind the immediate predecessor baseline to its immutable qualified bytes."""
    _relative_file(root, HISTORICAL_A12TIP_BASELINE_PATH)
    oid, content = _canonical_git_blob(root, HISTORICAL_A12TIP_BASELINE_PATH, source="HEAD")
    _require(_sha256(content) == HISTORICAL_A12TIP_SHA256, "historical A12TIP baseline SHA256 changed")
    _require(oid == HISTORICAL_A12TIP_GIT_BLOB, "historical A12TIP baseline Git blob changed")
    try:
        historical = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("historical A12TIP baseline is not valid JSON") from exc
    _require(isinstance(historical, dict), "historical A12TIP baseline must be a JSON object")
    _require(historical.get("candidate_file_count") == 429, "historical A12TIP candidate count changed")
    return oid, content


def _verify_historical_a12tcp_baseline(root: Path) -> tuple[str, bytes]:
    """Preserve the immutable immediate predecessor's canonical identity."""
    _relative_file(root, HISTORICAL_A12TCP_BASELINE_PATH)
    oid, content = _canonical_git_blob(root, HISTORICAL_A12TCP_BASELINE_PATH, source="HEAD")
    _require(_sha256(content) == HISTORICAL_A12TCP_SHA256, "historical A12TCP baseline SHA256 changed")
    _require(oid == HISTORICAL_A12TCP_GIT_BLOB, "historical A12TCP baseline Git blob changed")
    historical = json.loads(content)
    _require(historical.get("candidate_file_count") == 430, "historical A12TCP candidate count changed")
    return oid, content


def verify_successor_candidate_baseline(root: Path, expected_paths: set[str]) -> set[str]:
    """Validate the versioned, complete candidate identity without rewriting history."""
    path = root / SUCCESSOR_BASELINE_PATH
    _require(path.is_file() and not path.is_symlink(), "successor candidate baseline is missing or unsafe")
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("successor candidate baseline is not valid JSON") from exc
    _require(isinstance(baseline, dict), "successor candidate baseline must be a JSON object")
    _require(set(baseline) == _SUCCESSOR_KEYS, "successor candidate baseline keys do not match schema")
    _require(baseline["schema_version"] == 2, "unknown successor candidate baseline schema")
    _require(
        baseline["purpose"] == SUCCESSOR_BASELINE_PURPOSE,
        "successor candidate baseline purpose mismatch",
    )

    _verify_historical_a12fp_baseline(root)
    _verify_historical_a12tip_baseline(root)
    _verify_historical_a12tcp_baseline(root)
    predecessor = baseline["predecessor_baseline"]
    _require(isinstance(predecessor, dict), "successor predecessor identity must be an object")
    _require(set(predecessor) == _PREDECESSOR_KEYS, "invalid predecessor identity keys")
    _require(predecessor["path"] == HISTORICAL_A12TCP_BASELINE_PATH, "successor predecessor path mismatch")
    _relative_file(root, predecessor["path"])
    predecessor_oid, predecessor_bytes = _canonical_git_blob(
        root, predecessor["path"], source="HEAD"
    )
    _require(predecessor["sha256"] == _sha256(predecessor_bytes), "successor predecessor SHA256 mismatch")
    _require(predecessor["git_blob"] == predecessor_oid, "successor predecessor Git blob mismatch")
    _require(type(predecessor["size_bytes"]) is int, "invalid successor predecessor size")
    _require(predecessor["size_bytes"] == len(predecessor_bytes), "successor predecessor size mismatch")

    provenance = baseline["additive_provenance"]
    _require(isinstance(provenance, list), "successor additive provenance must be a list")
    expected_provenance = (
        (EXTENSION_PATH, PURPOSE),
        (AUTHORITY_EXTENSION_PATH, AUTHORITY_PURPOSE),
        (A10_EXTENSION_PATH, A10_PURPOSE),
        (A11_EXTENSION_PATH, A11_PURPOSE),
        (A12F_EXTENSION_PATH, A12F_PURPOSE),
        (A12TI_EXTENSION_PATH, A12TI_PURPOSE),
        (A12TC_EXTENSION_PATH, A12TC_PURPOSE),
        (A12TGI_EXTENSION_PATH, A12TGI_PURPOSE),
    )
    _require(len(provenance) == len(expected_provenance), "successor provenance history is incomplete")
    for item, (expected_path, expected_purpose) in zip(provenance, expected_provenance, strict=True):
        _require(isinstance(item, dict), "successor provenance entry must be an object")
        _require(set(item) == _SUCCESSOR_LINEAGE_KEYS, "invalid successor provenance entry keys")
        _require(item["path"] == expected_path, "successor provenance path/order mismatch")
        _require(item["purpose"] == expected_purpose, "successor provenance purpose mismatch")
        _relative_file(root, item["path"])
        source = "index" if expected_path in {
            A11_EXTENSION_PATH,
            A12F_EXTENSION_PATH,
            A12TI_EXTENSION_PATH,
            A12TC_EXTENSION_PATH,
            A12TGI_EXTENSION_PATH,
        } else "HEAD"
        oid, content = _canonical_git_blob(root, item["path"], source=source)
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
        oid, content = _canonical_git_blob(root, candidate_path, source="index")
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
    a11_extension_path = root / A11_EXTENSION_PATH
    a12f_extension_path = root / A12F_EXTENSION_PATH
    a12ti_extension_path = root / A12TI_EXTENSION_PATH
    a12tc_extension_path = root / A12TC_EXTENSION_PATH
    _require(base_path.is_file(), "frozen Gate738AD base manifest is missing")
    _require(extension_path.is_file(), "MAOS source extension metadata is missing")
    _require(authority_extension_path.is_file(), "MAOS Authority source extension metadata is missing")
    _require(a10_extension_path.is_file(), "MAOS A10 source extension metadata is missing")
    _require(a11_extension_path.is_file(), "MAOS A11 source extension metadata is missing")
    _require(a12f_extension_path.is_file(), "MAOS A12F source extension metadata is missing")
    _require(a12ti_extension_path.is_file(), "MAOS A12TI source extension metadata is missing")
    _require(a12tc_extension_path.is_file(), "MAOS A12TC source extension metadata is missing")
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
    try:
        a11_extension = json.loads(a11_extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS A11 source extension is not valid JSON") from exc
    a11_paths = verify_a11_source_extension(
        root, base_bytes, a11_extension,
        frozenset(kernel_paths | authority_paths | a10_paths),
    )
    try:
        a12f_extension = json.loads(a12f_extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS A12F source extension is not valid JSON") from exc
    a12f_paths = verify_a12f_source_extension(
        root,
        base_bytes,
        a12f_extension,
        frozenset(kernel_paths | authority_paths | a10_paths | a11_paths),
    )
    try:
        a12ti_extension = json.loads(a12ti_extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS A12TI source extension is not valid JSON") from exc
    a12ti_paths = verify_a12ti_source_extension(
        root,
        base_bytes,
        a12ti_extension,
        frozenset(kernel_paths | authority_paths | a10_paths | a11_paths | a12f_paths),
    )
    try:
        a12tc_extension = json.loads(a12tc_extension_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS A12TC source extension is not valid JSON") from exc
    a12tc_paths = verify_a12tc_source_extension(
        root,
        base_bytes,
        a12tc_extension,
        frozenset(kernel_paths | authority_paths | a10_paths | a11_paths | a12f_paths | a12ti_paths),
    )
    effective_paths = (
        base_paths
        | kernel_paths
        | authority_paths
        | a10_paths
        | a11_paths
        | a12f_paths
        | a12ti_paths
        | a12tc_paths
    )
    try:
        a12tgi_extension = json.loads((root / A12TGI_EXTENSION_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtensionError("MAOS A12TGI source extension is missing or invalid") from exc
    a12tgi_paths = verify_a12tgi_source_extension(
        root, base_bytes, a12tgi_extension, frozenset(effective_paths),
    )
    return verify_successor_candidate_baseline(root, effective_paths | a12tgi_paths)
