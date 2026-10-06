"""Static safety contracts for the Gate738AA migration surfaces."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import gate738p_contract_upgrade as runner

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@pytest.mark.parametrize("target", ["", "head", "20269999_9999"])
def test_canonical_runner_refuses_empty_head_and_unknown_targets_before_alembic(
    monkeypatch, target: str
):
    monkeypatch.setenv("EXPECTED_MIGRATION_HEAD", target)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test@127.0.0.1/gate738aa_no_connect")
    monkeypatch.setenv("GATE738P_ACTION", "")
    monkeypatch.setattr(
        runner,
        "_run_alembic",
        lambda _target: pytest.fail("refused target must not reach Alembic"),
    )

    with pytest.raises(RuntimeError, match="one explicit qualified target"):
        runner.main()


def test_migration_runner_is_in_image_and_runtime_evidence_is_external_read_only():
    dockerfile = _read("Dockerfile")
    compose = _read("docker-compose.yml")
    evidence_overlay = _read("compose.migration-evidence.example.yml")

    assert "COPY scripts/gate738p_contract_upgrade.py ./scripts/gate738p_contract_upgrade.py" in dockerfile
    assert 'command: ["python", "-B", "scripts/gate738p_contract_upgrade.py"]' in compose
    assert "profiles: [\"migration-gate\"]" in compose
    assert "GATE738P_HARD_CRASH_EVIDENCE_FILE: /run/migration-gate/qualification-evidence.json" in compose
    assert "GATE738P_HARD_CRASH_EVIDENCE_HOST_PATH:?" in evidence_overlay
    assert "read_only: true" in evidence_overlay
    assert "create_host_path: false" in evidence_overlay
    assert "GATE738P_HARD_CRASH_EVIDENCE_FILE" not in dockerfile


def test_ci_smoke_uses_only_an_explicit_allowed_pre_contract_target_and_gates_publish():
    workflow = _read(".github/workflows/ci.yml")
    staging = workflow.split("  staging-smoke:", maxsplit=1)[1].split("  dependency-audit:", maxsplit=1)[0]
    docker = workflow.split("  docker:", maxsplit=1)[1].split("  staging-smoke:", maxsplit=1)[0]

    assert "EXPECTED_MIGRATION_HEAD=20261004_0032" in staging
    assert "--profile migration-gate run --rm migrate" in staging
    assert staging.index("run --rm migrate") < staging.index("docker compose up -d --build api")
    assert "20260912_0021" not in staging
    assert "needs: [quality, migration-contract]" in staging
    assert "needs: [quality, staging-smoke]" in docker
    assert "gate738p_hard_crash_qualification.py" not in staging
    assert "Gate738L" not in staging

    local_smoke = _read("scripts/staging-smoke.ps1")
    assert "--profile migration-gate run --rm migrate" in local_smoke
    assert local_smoke.index("run --rm migrate") < local_smoke.index("docker compose up -d api")


def test_restore_wrapper_target_allowlist_matches_canonical_runner():
    restore = _read("scripts/restore-drill.ps1")
    match = re.search(
        r"\[ValidateSet\((.*?)\)\]\s*\[string\]\$MigrationTarget", restore, re.DOTALL
    )
    assert match is not None
    restore_targets = set(re.findall(r"'([^']+)'", match.group(1)))
    canonical_targets = {
        runner.EXPAND_TARGET,
        runner.CONTROL_TARGET,
        *runner.CONTRACT_TARGETS,
    }

    assert restore_targets == canonical_targets
    assert "gate738aa_restore_" in restore
    assert "Restore target refused" in restore
    assert "$databaseUri.Query -or $databaseUri.Fragment" in restore
    assert "scripts/gate738p_contract_upgrade.py" in restore
    assert "python -m alembic upgrade" not in restore
    assert "$response.migration_head -ne $MigrationTarget" in restore


def test_gate738p_admin_url_is_confined_before_connection_and_gate735b_is_exact():
    guard_tests = _read("tests/test_gate738p_contract_guard.py")
    class_enrollment_test = _read("tests/test_gate735b_class_enrollment_postgres.py")

    assert "parsed.hostname not in {\"localhost\", \"127.0.0.1\", \"::1\"}" in guard_tests
    assert 'database != "gate738p_admin"' in guard_tests
    assert "refused before connection" in guard_tests
    assert 'alembic("upgrade", "20261003_0026")' in class_enrollment_test
    assert not re.search(r'alembic\("upgrade",\s*"head"\)', class_enrollment_test)


def test_operational_docs_and_example_env_have_no_stale_or_direct_release_target():
    env_example = _read(".env.example")
    readme = _read("README.md")
    migrations = _read("docs/MIGRATIONS.md")
    operations = _read("docs/OPERATIONS.md")

    assert "EXPECTED_MIGRATION_HEAD=" in env_example
    assert "20260912_0021" not in env_example + readme
    assert "--profile migration-gate run --rm migrate" in migrations
    assert "python -m alembic upgrade <revision_id>" not in migrations + operations
    assert "backup production را منتقل یا restore نکنید" in operations
