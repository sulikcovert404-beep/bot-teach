from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "r2_offsite_packager.py"
spec = importlib.util.spec_from_file_location("r2_offsite_packager", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def make_plan(tmp_path: Path, *, mode: int = 0o600):
    source = tmp_path / "education.dump"
    source.write_bytes("دادهٔ آزمایشی فارسی\n".encode())
    source.chmod(mode)
    return module.PackagePlan(
        database="education",
        timestamp_utc="2026-09-08T20:00:00Z",
        source_dump=source,
        output_dir=tmp_path / "out",
    )


def test_canonical_json_is_stable_and_utf8(tmp_path: Path):
    plan = make_plan(tmp_path)
    manifest = module.build_manifest(plan)
    assert module.canonical_json(manifest) == module.canonical_json(dict(reversed(manifest.items())))
    assert "داده" not in module.canonical_json(manifest).decode("utf-8")
    assert manifest["plaintext_sha256"] == module.sha256_file(plan.source_dump)


def test_dry_run_has_no_side_effects(tmp_path: Path):
    plan = make_plan(tmp_path)
    result = module.prepare_package(plan, recipient=None, execute=False)
    assert result["status"] == "dry_run"
    assert not (tmp_path / "out").exists()


def test_execute_requires_recipient(tmp_path: Path):
    with pytest.raises(module.PackageError, match="recipient"):
        module.prepare_package(make_plan(tmp_path), recipient=None, execute=True)


def test_rejects_permissive_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(module.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    with pytest.raises(module.PackageError, match="permissive"):
        module.prepare_package(make_plan(tmp_path, mode=0o644), recipient="age1test", execute=True)
