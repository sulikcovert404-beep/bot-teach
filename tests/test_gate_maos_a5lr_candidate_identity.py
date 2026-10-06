from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1] / ".github" / "scripts" / "gate_maos_a5lr_candidate_identity.py"
)
SPEC = importlib.util.spec_from_file_location("gate_maos_a5lr_candidate_identity", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def _ci_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_WORKSPACE", str(MODULE_PATH.parents[2]))
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "123456789")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))


def test_ci_identity_requires_the_exact_compose_database_for_this_checkout(
    monkeypatch, tmp_path: Path
) -> None:
    _ci_env(monkeypatch, tmp_path)
    container_id = "b" * 64
    labels = {
        "com.docker.compose.service": "db",
        "com.docker.compose.project.working_dir": str(MODULE_PATH.parents[2]),
        "com.docker.compose.project.config_files": str(
            MODULE_PATH.parents[2] / "docker-compose.yml"
        ),
    }
    calls: list[list[str]] = []

    def fake_run(args, *, input_text=None):
        calls.append(args)
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return GATE.subprocess.CompletedProcess(args, 0, "a" * 40, "")
        if args[:4] == ["docker", "compose", "ps", "-q"]:
            return GATE.subprocess.CompletedProcess(args, 0, container_id, "")
        if args[:2] == ["docker", "inspect"]:
            return GATE.subprocess.CompletedProcess(args, 0, json.dumps(labels), "")
        raise AssertionError(args)

    monkeypatch.setattr(GATE, "_run", fake_run)

    assert GATE._ci_identity() == ("a5lr_123456789_2", "ci_a5lr_123456789_2")
    assert len(calls) == 3


def test_ci_identity_rejects_a_compose_database_outside_the_workspace(
    monkeypatch, tmp_path: Path
) -> None:
    _ci_env(monkeypatch, tmp_path)
    container_id = "b" * 64
    labels = {
        "com.docker.compose.service": "db",
        "com.docker.compose.project.working_dir": str(tmp_path),
        "com.docker.compose.project.config_files": str(tmp_path / "docker-compose.yml"),
    }

    def fake_run(args, *, input_text=None):
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return GATE.subprocess.CompletedProcess(args, 0, "a" * 40, "")
        if args[:4] == ["docker", "compose", "ps", "-q"]:
            return GATE.subprocess.CompletedProcess(args, 0, container_id, "")
        return GATE.subprocess.CompletedProcess(args, 0, json.dumps(labels), "")

    monkeypatch.setattr(GATE, "_run", fake_run)

    with pytest.raises(GATE.GateError, match="DISPOSABLE_COMPOSE_DATABASE_ATTESTATION_FAILED"):
        GATE._ci_identity()


def test_bootstrap_masks_ephemeral_credential_before_sql_and_writes_safe_outputs(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    credential = "Aa0_" + "b" * 39
    role = "a5lr_123456789_2"
    generation = "ci_a5lr_123456789_2"
    _ci_env(monkeypatch, tmp_path)
    monkeypatch.setattr(GATE, "_ci_identity", lambda: (role, generation))
    monkeypatch.setattr(GATE.secrets, "token_urlsafe", lambda _size: credential)
    statements: list[str] = []
    calls = 0

    def fake_psql(sql: str) -> str:
        nonlocal calls
        calls += 1
        statements.append(sql)
        if calls == 1:
            assert capsys.readouterr().out == f"::add-mask::{credential}\n"
            return "absent"
        if calls == 2:
            assert credential in sql
            return ""
        if calls in (3, 4):
            return GATE._CANDIDATE_ATTRIBUTES
        return "0"

    monkeypatch.setattr(GATE, "_psql", fake_psql)

    assert GATE.bootstrap_candidate() == (role, generation)
    assert "GRANT" not in "\n".join(statements).upper()
    assert "app_runtime" not in statements[1]
    outputs = (tmp_path / "github-output").read_text(encoding="utf-8")
    assert outputs == f"writer_role={role}\nwriter_generation={generation}\n"
    assert credential not in outputs
    assert capsys.readouterr().out == ""


def test_bootstrap_fails_closed_when_candidate_attributes_are_elevated(
    monkeypatch, tmp_path: Path
) -> None:
    _ci_env(monkeypatch, tmp_path)
    monkeypatch.setattr(GATE, "_ci_identity", lambda: ("a5lr_123456789_2", "ci_a5lr_123456789_2"))
    monkeypatch.setattr(GATE.secrets, "token_urlsafe", lambda _size: "a" * 43)
    results = iter(("absent", "", "1|1|1|0|0|0|0"))
    monkeypatch.setattr(GATE, "_psql", lambda _sql: next(results))

    with pytest.raises(GATE.GateError, match="DISPOSABLE_CANDIDATE_ROLE_ATTRIBUTES_MISMATCH"):
        GATE.bootstrap_candidate()


def test_verify_contract_is_read_only_and_requires_exact_0032_registration(monkeypatch) -> None:
    role = "a5lr_123456789_2"
    generation = "ci_a5lr_123456789_2"
    statements: list[str] = []
    results = iter(("20261004_0032", f"{generation}|{role}|SERVING\nlegacy|app_runtime|SERVING"))
    monkeypatch.setattr(GATE, "_role_attributes", lambda _role: GATE._CANDIDATE_ATTRIBUTES)

    def fake_psql(sql: str) -> str:
        statements.append(sql)
        return next(results)

    monkeypatch.setattr(GATE, "_psql", fake_psql)

    GATE.verify_contract(role, generation)

    assert len(statements) == 2
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)


def test_verify_contract_rejects_wrong_head_or_registration(monkeypatch) -> None:
    role = "a5lr_123456789_2"
    generation = "ci_a5lr_123456789_2"
    monkeypatch.setattr(GATE, "_role_attributes", lambda _role: GATE._CANDIDATE_ATTRIBUTES)
    results = iter(("20261004_0033", ""))
    monkeypatch.setattr(GATE, "_psql", lambda _sql: next(results))

    with pytest.raises(GATE.GateError, match="MIGRATION_HEAD_MISMATCH"):
        GATE.verify_contract(role, generation)


def test_workflow_orders_candidate_bootstrap_migration_checks_and_readiness() -> None:
    workflow = (MODULE_PATH.parents[1] / "workflows" / "ci.yml").read_text(encoding="utf-8")
    staging = workflow[workflow.index("  staging-smoke:") : workflow.index("\n  dependency-audit:")]
    candidate = staging.index("gate_maos_a5lr_candidate_identity.py bootstrap")
    migration = staging.index("docker compose --profile migration-gate run --rm migrate")
    contract = staging.index("gate_maos_a5lr_candidate_identity.py\n          verify-contract")
    pre_api = staging.index("gate_maos_a5k_runtime_identity.py pre-api-check")
    api_start = staging.index("docker compose up -d --build api")
    readiness = staging.index("- name: Wait for readiness and migration head")

    assert candidate < migration < contract < pre_api < api_start < readiness
    assert 'echo "EXPECTED_MIGRATION_HEAD=20261004_0032"' in staging
    assert 'EXPECTED_MIGRATION_HEAD: "20261004_0032"' in staging
    assert "WRITER_DATABASE_ROLE: ${{ steps.a5lr_candidate.outputs.writer_role }}" in staging
    assert "WRITER_GENERATION: ${{ steps.a5lr_candidate.outputs.writer_generation }}" in staging
    assert "for attempt in $(seq 1 45)" in staging
    assert "sleep 2" in staging
    readiness_step = staging[
        readiness : staging.index("- name: Capture redacted readiness evidence")
    ]
    assert '"migration_head"]' in readiness_step
    assert '"20261004_0032"' in readiness_step
    assert "alembic upgrade head" not in staging
