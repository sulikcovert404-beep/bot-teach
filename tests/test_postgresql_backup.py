from __future__ import annotations

from pathlib import Path

import pytest

from scripts.postgresql_backup import (
    build_plan,
    command_for,
    ensure_free_space,
    parse_args,
    run_backup,
)


def test_plan_is_outside_repository_and_has_manifest() -> None:
    plans = build_plan(Path("/var/backups/postgresql"), "20260908T030000Z", ("education", "mentorbot"))

    assert plans[0].dump_path == Path("/var/backups/postgresql/20260908T030000Z/education.dump")
    assert plans[1].manifest_path.name == "mentorbot.manifest.json"


def test_command_uses_partial_output_and_custom_format() -> None:
    plan = build_plan(Path("/backups"), "ts", ("education",))[0]

    assert command_for(plan) == (
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--file=/backups/ts/education.dump.partial",
        "education",
    )


def test_dry_run_is_default() -> None:
    assert parse_args([]).execute is False


def test_dry_run_does_not_create_output_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan = build_plan(tmp_path / "backups", "ts", ("education",))[0]

    run_backup(plan, "ts", execute=False)

    assert not plan.dump_path.parent.exists()
    assert "DRY_RUN" in capsys.readouterr().out


def test_plan_rejects_path_traversal_database_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe database"):
        build_plan(tmp_path, "ts", ("../education",))


def test_free_space_guard() -> None:
    with pytest.raises(RuntimeError, match="insufficient free space"):
        ensure_free_space(Path("."), 10**18)
