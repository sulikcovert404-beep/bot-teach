from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.gate738ad_maos_source_extension import (
    A10_EXTENSION_PATH,
    AUTHORITY_EXTENSION_PATH,
    BASE_MANIFEST_PATH,
    EXPECTED_A10_PATHS,
    EXPECTED_AUTHORITY_PATHS,
    EXPECTED_MAOS_PATHS,
    EXTENSION_PATH,
    SUCCESSOR_BASELINE_PATH,
    SourceExtensionError,
    load_effective_candidate_paths,
    verify_a10_source_extension,
    verify_authority_source_extension,
    verify_source_extension,
    verify_successor_candidate_baseline,
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
    assert effective == base_paths | EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS | EXPECTED_A10_PATHS
    assert EXPECTED_MAOS_PATHS.isdisjoint(base_paths)
    assert EXPECTED_AUTHORITY_PATHS.isdisjoint(base_paths | EXPECTED_MAOS_PATHS)
    assert EXPECTED_A10_PATHS.isdisjoint(base_paths | EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS)
    assert len(effective) == 426
    baseline = json.loads((ROOT / SUCCESSOR_BASELINE_PATH).read_text(encoding="utf-8"))
    assert baseline["candidate_file_count"] == 426
    assert {item["path"] for item in baseline["candidate_files"]} == effective


def _successor_fixture_root(tmp_path: Path) -> tuple[Path, dict[str, object], set[str]]:
    root = tmp_path / "successor"
    root.mkdir()
    source_paths = (
        BASE_MANIFEST_PATH,
        EXTENSION_PATH,
        AUTHORITY_EXTENSION_PATH,
        A10_EXTENSION_PATH,
    )
    for relative in source_paths:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        oid = subprocess.run(
            ["git", "rev-parse", "--verify", f"HEAD:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="ascii",
        ).stdout.strip()
        destination.write_bytes(
            subprocess.run(
                ["git", "cat-file", "blob", oid], cwd=ROOT, check=True, capture_output=True
            ).stdout
        )
    candidate_path = next(iter(EXPECTED_A10_PATHS))
    candidate = root / candidate_path
    candidate.parent.mkdir(parents=True, exist_ok=True)
    oid = subprocess.run(
        ["git", "rev-parse", "--verify", f"HEAD:{candidate_path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="ascii",
    ).stdout.strip()
    candidate.write_bytes(
        subprocess.run(
            ["git", "cat-file", "blob", oid], cwd=ROOT, check=True, capture_output=True
        ).stdout
    )

    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "core.autocrlf", "false"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Gate fixture"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "gate-fixture@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "add", "--", *source_paths, candidate_path], check=True
    )
    subprocess.run(
        ["git", "-C", str(root), "commit", "-qm", "fixture committed source identities"],
        check=True,
    )

    def canonical_blob(relative: str) -> tuple[str, bytes]:
        oid = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", f"HEAD:{relative}"],
            check=True,
            capture_output=True,
            text=True,
            encoding="ascii",
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", oid],
            check=True,
            capture_output=True,
        ).stdout
        return oid, blob

    _base_oid, base_bytes = canonical_blob(BASE_MANIFEST_PATH)
    provenance = []
    for relative, purpose in (
        (EXTENSION_PATH, "MAOS_KERNEL_V1"),
        (AUTHORITY_EXTENSION_PATH, "MAOS_AUTHORITY_V1"),
        (A10_EXTENSION_PATH, "MAOS_A10_PERSISTENCE_V1"),
    ):
        oid, content = canonical_blob(relative)
        provenance.append(
            {
                "path": relative,
                "purpose": purpose,
                "sha256": hashlib.sha256(content).hexdigest(),
                "git_blob": oid,
                "size_bytes": len(content),
            }
        )
    baseline: dict[str, object] = {
        "schema_version": 1,
        "purpose": "GATE738AD_SUCCESSOR_CANDIDATE_V1",
        "predecessor_manifest": {
            "path": BASE_MANIFEST_PATH,
            "sha256": hashlib.sha256(base_bytes).hexdigest(),
            "git_blob": _base_oid,
            "size_bytes": len(base_bytes),
        },
        "additive_provenance": provenance,
        "candidate_file_count": 1,
        "candidate_files": [],
    }
    entries = baseline["candidate_files"]
    assert isinstance(entries, list)
    candidate_oid, content = canonical_blob(candidate_path)
    entries.append(
        {
            "path": candidate_path,
            "git_blob": candidate_oid,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
    )
    (root / SUCCESSOR_BASELINE_PATH).write_text(json.dumps(baseline), encoding="utf-8")
    return root, baseline, {candidate_path}


def test_successor_baseline_is_exact_and_provenance_bound(tmp_path: Path) -> None:
    root, _baseline, expected = _successor_fixture_root(tmp_path)
    assert verify_successor_candidate_baseline(root, expected) == expected


def test_successor_provenance_is_invariant_to_crlf_checkout(tmp_path: Path) -> None:
    root, _baseline, expected = _successor_fixture_root(tmp_path)
    entries = _baseline["candidate_files"]
    assert isinstance(entries, list) and entries
    for relative in (A10_EXTENSION_PATH, entries[0]["path"]):
        path = root / relative
        committed = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", f"HEAD:{relative}"],
            check=True,
            capture_output=True,
        ).stdout
        assert b"\r\n" not in committed
        path.write_bytes(committed.replace(b"\n", b"\r\n"))
        assert path.read_bytes() != committed
    assert verify_successor_candidate_baseline(root, expected) == expected


def test_successor_baseline_rejects_altered_identity(tmp_path: Path) -> None:
    root, original, expected = _successor_fixture_root(tmp_path)
    cases = [
        ("candidate_sha", "candidate SHA256 mismatch"),
        ("candidate_blob", "candidate Git blob mismatch"),
        ("predecessor", "successor predecessor SHA256 mismatch"),
        ("lineage", "successor provenance purpose mismatch"),
        ("count", "successor candidate file count mismatch"),
    ]
    for mutate, message in cases:
        baseline = copy.deepcopy(original)
        if mutate == "candidate_sha":
            baseline["candidate_files"][0]["sha256"] = "0" * 64  # type: ignore[index]
        elif mutate == "candidate_blob":
            baseline["candidate_files"][0]["git_blob"] = "0" * 40  # type: ignore[index]
        elif mutate == "predecessor":
            baseline["predecessor_manifest"]["sha256"] = "0" * 64  # type: ignore[index]
        elif mutate == "lineage":
            baseline["additive_provenance"][0]["purpose"] = "unreviewed"  # type: ignore[index]
        else:
            baseline["candidate_file_count"] = 2
        (root / SUCCESSOR_BASELINE_PATH).write_text(json.dumps(baseline), encoding="utf-8")
        with pytest.raises(SourceExtensionError, match=message):
            verify_successor_candidate_baseline(root, expected)


def _a10_fixture_root(
    tmp_path: Path,
) -> tuple[Path, bytes, dict[str, object]]:
    root, base_bytes, _ = _fixture_root(tmp_path)
    for relative in EXPECTED_A10_PATHS:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    extension = json.loads((ROOT / A10_EXTENSION_PATH).read_text(encoding="utf-8"))
    return root, base_bytes, extension


def test_a10_extension_is_exact_and_bound_to_frozen_base() -> None:
    extension = json.loads((ROOT / A10_EXTENSION_PATH).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / BASE_MANIFEST_PATH).read_text(encoding="utf-8"))
    base_paths = {item["path"] for item in manifest["candidate_files"]}
    authority = json.loads((ROOT / AUTHORITY_EXTENSION_PATH).read_text(encoding="utf-8"))
    prior_paths = EXPECTED_MAOS_PATHS | {item["path"] for item in authority["files"]}
    paths = {item["path"] for item in extension["files"]}
    assert paths == EXPECTED_A10_PATHS
    assert paths.isdisjoint(base_paths | prior_paths)
    assert verify_a10_source_extension(
        ROOT,
        (ROOT / BASE_MANIFEST_PATH).read_bytes(),
        extension,
        frozenset(prior_paths),
    ) == base_paths | EXPECTED_A10_PATHS


def test_a10_missing_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    (root / next(iter(EXPECTED_A10_PATHS))).unlink()
    with pytest.raises(SourceExtensionError, match="missing, not a regular file"):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


def test_a10_unknown_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extra = "migrations/versions/20261006_9999_unapproved.py"
    (root / extra).write_text("revision = 'x'\n", encoding="utf-8")
    _refresh_entry(root, extension, 0, extra)
    with pytest.raises(SourceExtensionError, match="incomplete or contains unapproved paths"):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


def test_a10_duplicate_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["files"].append(copy.deepcopy(extension["files"][0]))
    with pytest.raises(SourceExtensionError, match="duplicate/conflicting extension path"):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sha256", "0" * 64, "SHA256 mismatch"),
        ("git_blob", "0" * 40, "Git blob mismatch"),
        ("size_bytes", -1, "source size mismatch"),
    ],
)
def test_a10_altered_metadata_fails_closed(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["files"][0][field] = value
    with pytest.raises(SourceExtensionError, match=message):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


def test_a10_wrong_base_identity_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["base_manifest_sha256"] = "0" * 64
    with pytest.raises(SourceExtensionError, match="extension base SHA256 mismatch"):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


def test_a10_overlap_with_previous_extension_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    overlap = "app/maos/authority_v1/contracts.py"
    destination = root / overlap
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / overlap, destination)
    _refresh_entry(root, extension, 0, overlap)
    with pytest.raises(SourceExtensionError, match="overlaps another source extension"):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


def test_a10_test_path_is_rejected(tmp_path: Path) -> None:
    root, base_bytes, extension = _a10_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    test_path = "tests/test_maos_a10_persistence_postgres.py"
    destination = root / test_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / test_path, destination)
    _refresh_entry(root, extension, 0, test_path)
    with pytest.raises(SourceExtensionError, match="outside approved namespace"):
        verify_a10_source_extension(
            root, base_bytes, extension, EXPECTED_MAOS_PATHS | EXPECTED_AUTHORITY_PATHS
        )


def _authority_fixture_root(
    tmp_path: Path,
) -> tuple[Path, bytes, dict[str, object]]:
    root, base_bytes, _ = _fixture_root(tmp_path)
    for relative in EXPECTED_AUTHORITY_PATHS:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    extension = json.loads(
        (ROOT / AUTHORITY_EXTENSION_PATH).read_text(encoding="utf-8")
    )
    return root, base_bytes, extension


def _refresh_entry(root: Path, extension: dict[str, object], index: int, path: str) -> None:
    content = (root / path).read_bytes()
    entries = extension["files"]
    assert isinstance(entries, list)
    entries[index] = {
        "path": path,
        "git_blob": hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def test_authority_extension_is_exact_and_metadata_is_bound() -> None:
    extension_path = ROOT / AUTHORITY_EXTENSION_PATH
    extension = json.loads(extension_path.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / BASE_MANIFEST_PATH).read_text(encoding="utf-8"))
    base_paths = {item["path"] for item in manifest["candidate_files"]}
    paths = {item["path"] for item in extension["files"]}
    assert paths == EXPECTED_AUTHORITY_PATHS
    assert not any(path.startswith("tests/") for path in paths)
    assert EXPECTED_AUTHORITY_PATHS.isdisjoint(base_paths | EXPECTED_MAOS_PATHS)
    assert verify_authority_source_extension(
        ROOT,
        (ROOT / BASE_MANIFEST_PATH).read_bytes(),
        extension,
    ) == base_paths | EXPECTED_AUTHORITY_PATHS


def test_authority_missing_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    (root / "app/maos/authority_v1/contracts.py").unlink()
    with pytest.raises(SourceExtensionError, match="missing, not a regular file"):
        verify_authority_source_extension(root, base_bytes, extension)


def test_authority_unknown_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    extra = "app/maos/authority_v1/unlisted.py"
    (root / extra).write_text("unlisted = True\n", encoding="utf-8")
    extension = copy.deepcopy(extension)
    _refresh_entry(root, extension, 0, extra)
    with pytest.raises(SourceExtensionError, match="incomplete or contains unapproved paths"):
        verify_authority_source_extension(root, base_bytes, extension)


def test_authority_duplicate_path_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    entries = extension["files"]
    assert isinstance(entries, list)
    entries.append(copy.deepcopy(entries[0]))
    with pytest.raises(SourceExtensionError, match="duplicate/conflicting extension path"):
        verify_authority_source_extension(root, base_bytes, extension)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sha256", "0" * 64, "SHA256 mismatch"),
        ("git_blob", "0" * 40, "Git blob mismatch"),
        ("size_bytes", -1, "source size mismatch"),
    ],
)
def test_authority_altered_metadata_fails_closed(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    entries = extension["files"]
    assert isinstance(entries, list)
    entries[0][field] = value
    with pytest.raises(SourceExtensionError, match=message):
        verify_authority_source_extension(root, base_bytes, extension)


def test_authority_wrong_base_identity_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    extension = copy.deepcopy(extension)
    extension["base_manifest_git_blob"] = "0" * 40
    with pytest.raises(SourceExtensionError, match="extension base Git blob mismatch"):
        verify_authority_source_extension(root, base_bytes, extension)


def test_authority_overlap_with_base_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    base_path = json.loads(base_bytes)["candidate_files"][0]["path"]
    source = ROOT / base_path
    destination = root / base_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    extension = copy.deepcopy(extension)
    _refresh_entry(root, extension, 0, base_path)
    with pytest.raises(SourceExtensionError, match="conflicts with frozen base path"):
        verify_authority_source_extension(root, base_bytes, extension)


def test_authority_overlap_with_kernel_extension_fails_closed(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    kernel_path = "app/maos/kernel_v1/tenant.py"
    extension = copy.deepcopy(extension)
    _refresh_entry(root, extension, 0, kernel_path)
    with pytest.raises(SourceExtensionError, match="overlaps another source extension"):
        verify_authority_source_extension(root, base_bytes, extension)


def test_authority_test_path_is_rejected(tmp_path: Path) -> None:
    root, base_bytes, extension = _authority_fixture_root(tmp_path)
    test_path = "tests/maos/test_authority_v1.py"
    destination = root / test_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / test_path, destination)
    extension = copy.deepcopy(extension)
    _refresh_entry(root, extension, 0, test_path)
    with pytest.raises(SourceExtensionError, match="outside approved namespace"):
        verify_authority_source_extension(root, base_bytes, extension)


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
    assert AUTHORITY_EXTENSION_PATH not in copy_sources
    assert A10_EXTENSION_PATH not in copy_sources
    assert "docs" not in copy_sources
