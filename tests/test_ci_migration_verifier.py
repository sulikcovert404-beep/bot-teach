"""Static safety contract for CI's disposable PostgreSQL migration verifier."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_migration_verifier_uses_disposable_postgres_and_explicit_revisions():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    quality = workflow.split("  quality:", maxsplit=1)[1].split("\n  docker:", maxsplit=1)[0]
    capabilities = quality.split(
        "      - name: Check disposable PostgreSQL capabilities", maxsplit=1
    )[1].split("      - name: Verify migration chain", maxsplit=1)[0]
    verifier = quality.split("      - name: Verify migration chain", maxsplit=1)[1]

    assert (
        "image: pgvector/pgvector:0.8.7-pg16@sha256:"
        "7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a"
    ) in quality
    assert "127.0.0.1:5432:5432" in quality
    assert 'SHOW server_version_num' in capabilities
    assert "EXPECTED_POSTGRESQL_MAJOR_16" in capabilities
    assert "pg_available_extensions" in capabilities
    assert "PGVECTOR_EXTENSION_UNAVAILABLE" in capabilities
    assert "CREATE EXTENSION" not in capabilities
    assert quality.index("Check disposable PostgreSQL capabilities") < quality.index(
        "Verify migration chain"
    )
    assert "postgresql+asyncpg://" in verifier
    assert "EXPECTED_MIGRATION_HEAD: 20261004_0033" in verifier
    assert "ROLLBACK_MIGRATION_TARGET: 20261003_0031" in verifier
    assert "alembic upgrade \"$EXPECTED_MIGRATION_HEAD\"" in verifier
    assert "alembic downgrade \"$ROLLBACK_MIGRATION_TARGET\"" in verifier
    assert "alembic downgrade -1" not in verifier
    assert "alembic upgrade head" not in verifier
    assert "sqlite:///" not in verifier
    assert "20260912_0021" not in verifier
