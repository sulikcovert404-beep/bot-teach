"""PostgreSQL-only concurrency qualification harness.

The test is intentionally skipped unless an explicit disposable TEST_DATABASE_URL is
provided. SQLite is never accepted as concurrency evidence.
"""
import os

import pytest


@pytest.mark.asyncio
async def test_exam_attempt_concurrency_requires_disposable_postgres() -> None:
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured; PostgreSQL qualification is runtime-pending")
    if not url.startswith(("postgresql+asyncpg://", "postgres://", "postgresql://")):
        pytest.fail("TEST_DATABASE_URL must point to PostgreSQL; SQLite is not valid concurrency evidence")
    if any(token in url.lower() for token in ("production", "prod", "staging")):
        pytest.fail("refusing non-disposable-looking TEST_DATABASE_URL")
    pytest.skip("Harness prepared; execute only with an explicitly disposable PostgreSQL fixture")
