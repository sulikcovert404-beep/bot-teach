from __future__ import annotations

from pathlib import Path

import pytest

from scripts.postgresql_backup import build_plan, command_for, ensure_free_space, parse_args


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


def test_free_space_guard() -> None:
    with pytest.raises(RuntimeError, match="insufficient free space"):
        ensure_free_space(Path("."), 10**18)
