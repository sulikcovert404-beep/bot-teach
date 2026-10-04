from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "requirements-linux-py312.lock"


def _lock_entries() -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^ ]+) --hash=sha256:([0-9a-f]{64})$")
    for line in LOCK_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        assert match, f"unlocked or malformed dependency line: {line!r}"
        name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
        assert name not in entries
        entries[name] = (match.group(2), match.group(3))
    return entries


def test_image_install_uses_platform_lock_and_pinned_build_backend() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = _lock_entries()

    assert "@sha256:" in next(line for line in dockerfile.splitlines() if line.startswith("FROM "))
    assert not any(line.lstrip().startswith("ARG ") for line in dockerfile.splitlines())
    assert not any(line.startswith("ADD ") for line in dockerfile.splitlines())
    assert "COPY pyproject.toml requirements-linux-py312.lock ./" in dockerfile
    assert "--require-hashes -r requirements-linux-py312.lock" in dockerfile
    assert "--no-deps --no-build-isolation ." in dockerfile
    assert "ai-education-platform-iran" not in lock

    build_requires = pyproject["build-system"]["requires"]
    for requirement in build_requires:
        name, version = requirement.split("==", maxsplit=1)
        assert lock[re.sub(r"[-_.]+", "-", name).lower()][0] == version


def test_docker_copy_sources_are_candidate_manifest_covered() -> None:
    manifest = json.loads((ROOT / "docs/GATE738AD_CANDIDATE_MANIFEST.json").read_text())
    candidate_paths = {item["path"] for item in manifest["candidate_files"]}
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_sources: list[str] = []
    for line in dockerfile.splitlines():
        if not line.startswith("COPY "):
            continue
        fields = line.split()
        copy_sources.extend(fields[1:-1])

    ignored_parts = {"__pycache__", ".venv", "tests", "tmp", "temp"}
    ignored_suffixes = {".pyc", ".pyo", ".pyd"}
    for source in copy_sources:
        path = ROOT / source
        assert path.exists(), f"COPY source is missing: {source}"
        paths = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        for candidate in paths:
            relative = candidate.relative_to(ROOT)
            if any(part in ignored_parts for part in relative.parts):
                continue
            if candidate.suffix in ignored_suffixes or candidate.name.startswith(".env"):
                continue
            assert relative.as_posix() in candidate_paths, relative.as_posix()


def test_qualification_evidence_and_local_artifacts_are_excluded() -> None:
    patterns = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())
    required = {
        ".env",
        ".env.*",
        "*.env",
        "**/*.env",
        "*.pem",
        "*.key",
        "*.crt",
        "*.cer",
        "*.p12",
        "*.pfx",
        "id_rsa*",
        "id_ed25519*",
        "*credentials*",
        "*secret*",
        "tmp/",
        "temp/",
        "**/tmp/",
        "**/temp/",
        "*.tar",
        "**/*.tar",
        "*.dump",
        "**/*.dump",
        "*.sqlite*",
        "**/*.sqlite*",
        "*.db",
        "**/*.db",
        "docs/GATE738P_HARD_CRASH_EVIDENCE.json",
    }
    assert required <= patterns

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pip install --require-hashes -r requirements-linux-py312.lock" in workflow
