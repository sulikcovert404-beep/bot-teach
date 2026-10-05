"""Static safety contract for CI's disposable PostgreSQL migration verifier."""

from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IMAGE = (
    "pgvector/pgvector:0.8.7-pg16@sha256:"
    "7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a"
)
EXPECTED_DATABASE_URL = (
    "postgresql+asyncpg://ci_migrations:ci_only_ephemeral_migrations_password"
    "@127.0.0.1:5432/ai_teacher_migrations"
)


def _step(quality, name):
    return next((step for step in quality["steps"] if step.get("name") == name), None)


def _database_is_ci_local(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "postgresql+asyncpg"
        and parsed.hostname == "127.0.0.1"
        and parsed.port == 5432
        and parsed.username == "ci_migrations"
        and parsed.password == "ci_only_ephemeral_migrations_password"
        and parsed.path == "/ai_teacher_migrations"
    )


def _vector_assertion_is_present(step):
    if step is None or not _database_is_ci_local(step.get("env", {}).get("DATABASE_URL")):
        return False

    run = step.get("run", "").lower()
    normalized = " ".join(run.split())
    return (
        "select extversion from pg_extension where extname = 'vector'" in normalized
        and "len(rows) != 1" in normalized
        and 'rows[0]["extversion"]' in normalized
        and "raise systemexit(" in normalized
    )


def _migration_contract_violations(workflow):
    violations = []
    quality = workflow.get("jobs", {}).get("quality", {})
    services = quality.get("services", {})
    postgres = services.get("postgres", {})
    postgres_env = postgres.get("env", {})

    if postgres.get("image") != EXPECTED_IMAGE:
        violations.append("postgres image must retain the approved immutable pgvector/PG16 digest")
    if postgres_env != {
        "POSTGRES_USER": "ci_migrations",
        "POSTGRES_PASSWORD": "ci_only_ephemeral_migrations_password",
        "POSTGRES_DB": "ai_teacher_migrations",
    }:
        violations.append("postgres service must use only its synthetic CI database identity")
    if "127.0.0.1:5432:5432" not in postgres.get("ports", []):
        violations.append("postgres service must bind only to loopback")

    steps = quality.get("steps", [])
    names = [step.get("name", "") for step in steps]
    required_names = [
        "Check disposable PostgreSQL capabilities",
        "Verify disposable app_runtime role prerequisite",
        "Verify migration chain",
        "Verify pgvector installed after migration",
        "Verify migration rollback and re-upgrade",
        "Verify pgvector installed after re-upgrade",
    ]
    missing_names = [name for name in required_names if name not in names]
    if missing_names:
        return violations + [f"required isolated migration-verification step is missing: {name}" for name in missing_names]

    positions = [names.index(name) for name in required_names]
    if positions != sorted(positions):
        violations.append("capability check, role prerequisite, explicit migration, rollback, and assertions are out of order")

    role_bootstrap = _step(quality, required_names[1])
    if role_bootstrap:
        if not _database_is_ci_local(role_bootstrap.get("env", {}).get("DATABASE_URL")):
            violations.append("app_runtime prerequisite must target only its synthetic loopback PostgreSQL service")
        if role_bootstrap.get("run") != "python -B tests/ci_bootstrap_app_runtime.py":
            violations.append("app_runtime prerequisite must use the reviewed CI-only bootstrap helper")

    pre_migration_run = "\n".join(
        step.get("run", "") for step in steps[positions[0] : positions[2]]
    )
    if "CREATE EXTENSION" in pre_migration_run.upper():
        violations.append("pre-migration setup must not execute CREATE EXTENSION")

    capabilities = _step(quality, required_names[0])
    capability_run = capabilities.get("run", "") if capabilities else ""
    if (
        "SHOW server_version_num" not in capability_run
        or "pg_available_extensions" not in capability_run
        or "EXPECTED_POSTGRESQL_MAJOR_16" not in capability_run
        or "PGVECTOR_EXTENSION_UNAVAILABLE" not in capability_run
        or "CREATE EXTENSION" in capability_run.upper()
    ):
        violations.append("read-only PostgreSQL 16/vector availability precheck is missing or mutating")

    migration = _step(quality, required_names[2])
    rollback = _step(quality, required_names[4])
    if migration:
        migration_env = migration.get("env", {})
        migration_run = migration.get("run", "")
        if not _database_is_ci_local(migration_env.get("DATABASE_URL")):
            violations.append("migration verifier must target only its synthetic loopback PostgreSQL service")
        if migration_env.get("EXPECTED_MIGRATION_HEAD") != "20261004_0033":
            violations.append("migration target must be explicit revision 20261004_0033")
        if (
            'alembic upgrade "$EXPECTED_MIGRATION_HEAD"' not in migration_run
            or 'test "$(python -m alembic current 2>/dev/null | awk \'{print $1}\')" = "$EXPECTED_MIGRATION_HEAD"'
            not in migration_run
        ):
            violations.append("migration must explicitly upgrade and verify revision 20261004_0033")
        if "upgrade head" in migration_run.lower() or "sqlite:///" in migration_run.lower():
            violations.append("migration verifier must not use upgrade head or SQLite")

    if rollback:
        rollback_env = rollback.get("env", {})
        rollback_run = rollback.get("run", "")
        if not _database_is_ci_local(rollback_env.get("DATABASE_URL")):
            violations.append("rollback verifier must target only its synthetic loopback PostgreSQL service")
        if rollback_env.get("EXPECTED_MIGRATION_HEAD") != "20261004_0033":
            violations.append("re-upgrade target must be explicit revision 20261004_0033")
        if rollback_env.get("ROLLBACK_MIGRATION_TARGET") != "20261003_0031":
            violations.append("rollback target must be explicit revision 20261003_0031")
        if (
            'alembic downgrade "$ROLLBACK_MIGRATION_TARGET"' not in rollback_run
            or 'alembic upgrade "$EXPECTED_MIGRATION_HEAD"' not in rollback_run
            or 'test "$(python -m alembic current 2>/dev/null | awk \'{print $1}\')" = "$ROLLBACK_MIGRATION_TARGET"'
            not in rollback_run
            or 'test "$(python -m alembic current 2>/dev/null | awk \'{print $1}\')" = "$EXPECTED_MIGRATION_HEAD"'
            not in rollback_run
        ):
            violations.append("rollback/re-upgrade must use both explicit qualified revisions")
        if "upgrade head" in rollback_run.lower() or "sqlite:///" in rollback_run.lower():
            violations.append("rollback verifier must not use upgrade head or SQLite")

    for name in (required_names[3], required_names[5]):
        assertion = _step(quality, name)
        if not _vector_assertion_is_present(assertion):
            violations.append(f"{name} must independently verify installed vector and nonempty extversion")

    # Limit this destination audit to the service and migration-verifier steps.
    # Other jobs intentionally have separate staging/release behavior.
    scoped_objects = [postgres]
    scoped_objects.extend(_step(quality, name) for name in required_names)
    scoped_text = "\n".join(str(item) for item in scoped_objects if item is not None).lower()
    if any(marker in scoped_text for marker in ("codesho", "production", "staging", "secrets.")):
        violations.append("migration verifier must not reference shared, Production, Staging, or secret DB bindings")
    for item in scoped_objects:
        if item is None:
            continue
        for key, value in item.get("env", {}).items():
            if "DATABASE_URL" in key and not _database_is_ci_local(value):
                violations.append("every migration-check DATABASE_URL must resolve to its isolated CI service")
                break

    return violations


def _load_workflow():
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


def test_ci_migration_verifier_satisfies_isolated_postgres_contract():
    assert _migration_contract_violations(_load_workflow()) == []


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        ("digest", "immutable pgvector/PG16 digest"),
        ("availability", "step is missing"),
        ("manual_extension", "pre-migration setup"),
        ("post_upgrade", "after migration"),
        ("post_reupgrade", "after re-upgrade"),
        ("shared_host", "loopback PostgreSQL service"),
        ("production_reference", "shared, Production, Staging"),
        ("staging_reference", "shared, Production, Staging"),
        ("upgrade_head", "explicitly upgrade"),
        ("wrong_target", "20261004_0033"),
        ("runtime_bootstrap_missing", "step is missing"),
        ("runtime_bootstrap_after_migration", "out of order"),
        ("runtime_bootstrap_shared_database", "synthetic loopback PostgreSQL"),
        ("runtime_bootstrap_wrong_database", "synthetic loopback PostgreSQL"),
        ("runtime_bootstrap_arbitrary_command", "reviewed CI-only bootstrap helper"),
        ("runtime_bootstrap_shared_reference", "shared, Production, Staging"),
    ],
)
def test_ci_migration_verifier_rejects_unsafe_contract_mutations(mutate, expected_fragment):
    workflow = deepcopy(_load_workflow())
    quality = workflow["jobs"]["quality"]
    steps = quality["steps"]
    by_name = {step.get("name"): step for step in steps}

    if mutate == "digest":
        quality["services"]["postgres"]["image"] = "postgres:16"
    elif mutate == "availability":
        steps.remove(by_name["Check disposable PostgreSQL capabilities"])
    elif mutate == "manual_extension":
        by_name["Check disposable PostgreSQL capabilities"]["run"] += "\nCREATE EXTENSION vector;"
    elif mutate == "post_upgrade":
        steps.remove(by_name["Verify pgvector installed after migration"])
    elif mutate == "post_reupgrade":
        steps.remove(by_name["Verify pgvector installed after re-upgrade"])
    elif mutate == "shared_host":
        by_name["Verify migration chain"]["env"]["DATABASE_URL"] = (
            EXPECTED_DATABASE_URL.replace("127.0.0.1", "shared-db")
        )
    elif mutate == "production_reference":
        by_name["Verify migration chain"]["env"]["DATABASE_URL"] = (
            EXPECTED_DATABASE_URL.replace("127.0.0.1", "production-db")
        )
    elif mutate == "staging_reference":
        by_name["Verify migration chain"]["env"]["DATABASE_URL"] = (
            EXPECTED_DATABASE_URL.replace("127.0.0.1", "staging-db")
        )
    elif mutate == "upgrade_head":
        by_name["Verify migration chain"]["run"] = "python -m alembic upgrade head"
    elif mutate == "wrong_target":
        by_name["Verify migration chain"]["env"]["EXPECTED_MIGRATION_HEAD"] = "20261003_0031"
    elif mutate == "runtime_bootstrap_missing":
        steps.remove(by_name["Verify disposable app_runtime role prerequisite"])
    elif mutate == "runtime_bootstrap_after_migration":
        steps.remove(by_name["Verify disposable app_runtime role prerequisite"])
        steps.insert(
            steps.index(by_name["Verify migration chain"]) + 1,
            by_name["Verify disposable app_runtime role prerequisite"],
        )
    elif mutate == "runtime_bootstrap_shared_database":
        by_name["Verify disposable app_runtime role prerequisite"]["env"]["DATABASE_URL"] = (
            EXPECTED_DATABASE_URL.replace("127.0.0.1", "shared-db")
        )
    elif mutate == "runtime_bootstrap_wrong_database":
        by_name["Verify disposable app_runtime role prerequisite"]["env"]["DATABASE_URL"] = (
            EXPECTED_DATABASE_URL.replace("ai_teacher_migrations", "production")
        )
    elif mutate == "runtime_bootstrap_arbitrary_command":
        by_name["Verify disposable app_runtime role prerequisite"]["run"] = "python scripts/admin.py"
    elif mutate == "runtime_bootstrap_shared_reference":
        by_name["Verify disposable app_runtime role prerequisite"]["env"]["DATABASE_URL"] += " # staging"

    violations = _migration_contract_violations(workflow)
    assert any(expected_fragment in violation for violation in violations), violations
