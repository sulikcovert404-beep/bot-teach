from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "scripts"
    / "gate_maos_a5k_runtime_identity.py"
)
SPEC = importlib.util.spec_from_file_location(
    "gate_maos_a5k_runtime_identity", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def test_runtime_url_is_restricted_to_api_app_runtime_disposable_database() -> None:
    assert GATE._runtime_credential(
        "postgresql+asyncpg://app_runtime:ci-only@db:5432/education"
    ) == "ci-only"
    assert GATE._runtime_credential(
        "postgresql+asyncpg://app_runtime:ci%2Donly@db:5432/education"
    ) == "ci-only"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://postgres:secret@db:5432/education",
        "postgresql+asyncpg://app_runtime:secret@external:5432/education",
        "postgresql+asyncpg://app_runtime:secret@db:5432/other",
        "postgresql+asyncpg://app_runtime@db:5432/education",
        "postgresql+asyncpg://app_runtime:secret@db:5433/education",
        "postgresql+asyncpg://app_runtime:secret@db:5432/education?sslmode=require",
    ],
)
def test_runtime_url_rejects_wrong_or_ambiguous_database_target(url: str) -> None:
    with pytest.raises(GATE.GateError):
        GATE._runtime_credential(url)


def test_password_literal_escapes_sql_metacharacters() -> None:
    literal = GATE._password_sql_literal("first'\\second")
    assert literal == "E'first\\'\\\\second'"
    assert "first'\\second" not in literal


def test_bootstrap_refuses_to_mutate_if_role_already_exists(monkeypatch) -> None:
    statements: list[str] = []

    def psql(sql: str) -> str:
        statements.append(sql)
        return "present"

    monkeypatch.setattr(GATE, "_psql", psql)
    with pytest.raises(GATE.GateError, match="APP_RUNTIME_ROLE_ALREADY_PRESENT"):
        GATE.bootstrap_role("not-logged")
    assert len(statements) == 1
    assert not any(statement.startswith("CREATE ROLE") for statement in statements)


def test_bootstrap_creates_only_identity_attributes_and_verifies_them(monkeypatch) -> None:
    statements: list[str] = []
    results = iter(("absent", "CREATE ROLE", GATE._ROLE_ATTRIBUTES))

    def psql(sql: str) -> str:
        statements.append(sql)
        return next(results)

    monkeypatch.setattr(GATE, "_psql", psql)
    GATE.bootstrap_role("runtime-secret")

    create_statement = statements[1]
    assert "CREATE ROLE app_runtime LOGIN" in create_statement
    assert "PASSWORD E' runtime-secret'" not in create_statement
    assert "PASSWORD E'runtime-secret'" in create_statement
    assert all(
        attribute in create_statement
        for attribute in (
            "NOSUPERUSER",
            "NOCREATEDB",
            "NOCREATEROLE",
            "NOREPLICATION",
            "NOBYPASSRLS",
        )
    )
    assert "GRANT " not in create_statement.upper()


def test_pre_api_probe_is_read_only_and_emits_only_allowlisted_values() -> None:
    compile(GATE._PRE_API_PROBE, "<gate-maos-a5k-probe>", "exec")
    assert "SELECT session_user, current_user, current_database()" in GATE._PRE_API_PROBE
    assert "SELECT version_num FROM public.alembic_version" in GATE._PRE_API_PROBE
    assert "print(error)" not in GATE._PRE_API_PROBE
    assert "get_settings().database_url" in GATE._PRE_API_PROBE


def test_pre_api_check_redacts_untrusted_container_output(monkeypatch, capsys) -> None:
    result = GATE.subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout=(
            "untrusted DATABASE_URL=secret-value\n"
            "A5K_RUNTIME_IDENTITY=PASS\n"
            "A5K_ALEMBIC_VERSION_READ=FAIL SQLSTATE=42501\n"
        ),
        stderr="secret-value",
    )
    monkeypatch.setattr(GATE, "_run", lambda *args, **kwargs: result)

    with pytest.raises(
        GATE.GateError, match="APP_RUNTIME_ALEMBIC_VERSION_PRIVILEGE_OR_READ_FAILED"
    ):
        GATE.pre_api_check()

    output = capsys.readouterr().out
    assert "A5K_RUNTIME_IDENTITY=PASS" in output
    assert "A5K_ALEMBIC_VERSION_READ=FAIL SQLSTATE=42501" in output
    assert "secret-value" not in output
    assert "DATABASE_URL" not in output


def test_workflow_orders_bootstrap_migration_and_pre_api_check() -> None:
    workflow = (MODULE_PATH.parents[1] / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    bootstrap = workflow.index("gate_maos_a5k_runtime_identity.py bootstrap-role")
    migration = workflow.index("docker compose --profile migration-gate run --rm migrate")
    pre_api = workflow.index("gate_maos_a5k_runtime_identity.py pre-api-check")
    api_start = workflow.index("docker compose up -d --build api")

    assert bootstrap < migration < pre_api < api_start
    assert 'echo "EXPECTED_MIGRATION_HEAD=20261004_0032"' in workflow
