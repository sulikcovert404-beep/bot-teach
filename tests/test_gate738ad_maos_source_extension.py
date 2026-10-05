from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.gate738ad_maos_source_extension import (
    BASE_MANIFEST_PATH,
    EXPECTED_MAOS_PATHS,
    EXTENSION_PATH,
    SourceExtensionError,
    load_effective_candidate_paths,
    verify_source_extension,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture_root(tmp_path: Path) -> tuple[Path, bytes, dict[str, object]]:
    root = tmp_path / "repo"
    root.mkdir()
    base_bytes = (ROOT / BASE_MANIFEST_PATH).read_bytes()
    (root / "docs").mkdir()
    (root / BASE_MANIFEST_PATH).write_bytes(base_bytes)
    (root / "app/maos/kernel_v1").mkdir(parents=True)
    for relative in EXPECTED_MAOS_PATHS:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    shutil.copyfile(ROOT / "Dockerfile", root / "Dockerfile")
    extension = json.loads((ROOT / EXTENSION_PATH).read_text(encoding="utf-8"))
    return root, base_bytes, extension


def test_unchanged_historical_base_and_authorized_extension_pass() -> None:
    effective = load_effective_candidate_paths(ROOT)
    manifest = json.loads((ROOT / BASE_MANIFEST_PATH).read_text(encoding="utf-8"))
    base_paths = {item["path"] for item in manifest["candidate_files"]}
    assert effective == base_paths | EXPECTED_MAOS_PATHS
    assert EXPECTED_MAOS_PATHS.isdisjoint(base_paths)


def test_missing_extension_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    (root / "app/maos/kernel_v1/tenant.py").unlink()
    with pytest.raises(SourceExtensionError, match="missing, not a regular file"):
        verify_source_extension(root, base_bytes, extension)


def test_extension_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["files"][0]["sha256"] = "0" * 64  # type: ignore[index]
    with pytest.raises(SourceExtensionError, match="SHA256 mismatch"):
        verify_source_extension(root, base_bytes, extension)


def test_extension_git_blob_mismatch_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["files"][0]["git_blob"] = "0" * 40  # type: ignore[index]
    with pytest.raises(SourceExtensionError, match="Git blob mismatch"):
        verify_source_extension(root, base_bytes, extension)


def test_unknown_schema_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["schema_version"] = 2
    with pytest.raises(SourceExtensionError, match="unknown source extension schema"):
        verify_source_extension(root, base_bytes, extension)


def test_unknown_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    extra_path = root / "app/maos/kernel_v1/unlisted.py"
    extra_path.write_text("unlisted = True\n", encoding="utf-8")
    content = extra_path.read_bytes()
    extension = copy.deepcopy(extension)
    extension["files"].append(  # type: ignore[union-attr]
        {
            "path": "app/maos/kernel_v1/unlisted.py",
            "git_blob": hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest(),
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
    )
    with pytest.raises(SourceExtensionError, match="incomplete or contains unapproved paths"):
        verify_source_extension(root, base_bytes, extension)


def test_conflicting_duplicate_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["files"].append(copy.deepcopy(extension["files"][0]))  # type: ignore[union-attr]
    with pytest.raises(SourceExtensionError, match="duplicate/conflicting extension path"):
        verify_source_extension(root, base_bytes, extension)


def test_wrong_base_identity_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["base_manifest_sha256"] = "0" * 64
    with pytest.raises(SourceExtensionError, match="extension base SHA256 mismatch"):
        verify_source_extension(root, base_bytes, extension)


def test_modified_frozen_base_bytes_fail_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _fixture_root(tmp_path)
    with pytest.raises(SourceExtensionError, match="frozen Gate738AD base manifest SHA256 mismatch"):
        verify_source_extension(root, base_bytes + b" ", extension)


def test_metadata_is_not_in_docker_image_copy_sources() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_sources = {
        source
        for line in dockerfile.splitlines()
        if line.startswith("COPY ")
        for source in line.split()[1:-1]
    }
    assert EXTENSION_PATH not in copy_sources
    assert "docs" not in copy_sources
