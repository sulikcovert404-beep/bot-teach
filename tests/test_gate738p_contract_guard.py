"""Gate738P fail-closed guard matrix on an explicit disposable PostgreSQL."""

from __future__ import annotations

import asyncio
import io
import os
import subprocess
import sys
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
import pytest

from scripts import gate738p_contract_upgrade as upgrade_runner


async def _run_alembic(environment: dict[str, str], revision: str) -> subprocess.CompletedProcess[str]:
    return await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-B", "-m", "alembic", "upgrade", revision],
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def _admin_dsn() -> str | None:
    value = os.environ.get("GATE738P_ADMIN_URL", "").strip()
    if not value:
        return None
    parsed = urlsplit(value)
    database = parsed.path.removeprefix("/")
    if (
        parsed.scheme not in {"postgresql", "postgresql+asyncpg"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or database != "gate738p_admin"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "GATE738P_ADMIN_URL refused before connection; use loopback and the gate738p_admin database"
        )
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://admin@db.example/gate738p_admin",
        "postgresql://admin@127.0.0.1/postgres",
        "postgresql://admin@127.0.0.1/gate738p_admin?options=unsafe",
        "postgresql://admin@127.0.0.1/gate738p_admin#fragment",
    ],
)
def test_admin_url_rejects_non_gate_or_non_loopback_target(monkeypatch, url: str):
    monkeypatch.setenv("GATE738P_ADMIN_URL", url)
    with pytest.raises(ValueError, match="refused before connection"):
        _admin_dsn()


def test_admin_url_accepts_only_gate_owned_loopback_namespace(monkeypatch):
    monkeypatch.setenv(
        "GATE738P_ADMIN_URL",
        "postgresql+asyncpg://gate_admin:local-only@127.0.0.1:5432/gate738p_admin",
    )
    assert _admin_dsn() == "postgresql://gate_admin:local-only@127.0.0.1:5432/gate738p_admin"


def test_contract_runner_requires_current_candidate_health(monkeypatch):
    monkeypatch.setenv("WRITER_ADMISSION_ENABLED", "true")
    monkeypatch.setenv("WRITER_GENERATION", "candidate-a")
    monkeypatch.setenv("WRITER_INSTANCE_ID", "instance1")
    monkeypatch.setenv("WRITER_DATABASE_ROLE", "candidate_role")
    monkeypatch.setenv("GATE738P_CANDIDATE_HEALTH_URL", "http://candidate/health/ready")

    class Response(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(
        upgrade_runner,
        "urlopen",
        lambda *_args, **_kwargs: Response(b'{"status":"ready","migration_head":"20261004_0032","writer_identity_verified":true}'),
    )
    upgrade_runner._candidate_ready("20261004_0032")


def test_contract_runner_rejects_stale_candidate_health(monkeypatch):
    monkeypatch.setenv("WRITER_ADMISSION_ENABLED", "true")
    monkeypatch.setenv("WRITER_GENERATION", "candidate-a")
    monkeypatch.setenv("WRITER_INSTANCE_ID", "instance1")
    monkeypatch.setenv("WRITER_DATABASE_ROLE", "candidate_role")
    monkeypatch.setenv("GATE738P_CANDIDATE_HEALTH_URL", "http://candidate/health/ready")

    class Response(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(
        upgrade_runner,
        "urlopen",
        lambda *_args, **_kwargs: Response(b'{"status":"ready","migration_head":"20261004_0029","writer_identity_verified":true}'),
    )
    with pytest.raises(RuntimeError, match="exact required migration head"):
        upgrade_runner._candidate_ready("20261004_0032")


@pytest.mark.parametrize(
    ("case", "expected_reason"),
    [
        ("legacy_serving", "legacy generation is not FENCED"),
        ("legacy_draining", "legacy generation is not FENCED"),
        ("candidate_missing", "candidate generation is missing"),
        ("candidate_not_serving", "candidate generation is missing"),
        ("second_admissible_generation", "another writer generation remains"),
        ("old_transaction", "OLD-generation database transaction remains active"),
        ("candidate_spoof", ""),
        ("public_execute", "executable by PUBLIC"),
        ("valid_candidate", ""),
    ],
)
def test_guarded_contract_precondition_matrix(case: str, expected_reason: str):
    admin_dsn = _admin_dsn()
    if not admin_dsn:
        pytest.skip("Explicit Gate738P disposable PostgreSQL URL required")
    database = "gate738p_" + uuid4().hex
    environment = os.environ.copy()
    environment["DATABASE_URL"] = admin_dsn.replace("postgresql://", "postgresql+asyncpg://", 1).rsplit("/", 1)[0] + f"/{database}"
    environment["WRITER_GENERATION"] = "candidate_p"
    role = "gate738p_candidate_" + uuid4().hex[:12]
    environment["WRITER_DATABASE_ROLE"] = role

    async def exercise() -> None:
        admin = await asyncpg.connect(admin_dsn)
        blocker_connection = None
        candidate_connection = None
        target_dsn = admin_dsn.rsplit("/", 1)[0] + f"/{database}"
        try:
            await admin.execute(f'CREATE DATABASE "{database}"')
            if not await admin.fetchval("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime'"):
                await admin.execute(
                    "CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS "
                    "NOCREATEDB NOCREATEROLE NOREPLICATION"
                )
            await admin.execute(f'CREATE ROLE "{role}" LOGIN INHERIT NOSUPERUSER NOBYPASSRLS')
            await admin.execute(f'GRANT app_runtime TO "{role}"')
            prepare = await _run_alembic(environment, "20261004_0032")
            assert prepare.returncode == 0, "preparation migration failed in disposable database"

            connection = await asyncpg.connect(target_dsn)
            try:
                await connection.execute("""
                    UPDATE public.submission_revision_backfill_state
                       SET status='VALIDATED' WHERE singleton=true;
                    UPDATE public.ai_teacher_writer_generation_state
                       SET state='FENCED' WHERE generation='legacy';
                """)
                if case == "legacy_serving":
                    await connection.execute("UPDATE public.ai_teacher_writer_generation_state SET state='SERVING' WHERE generation='legacy'")
                elif case == "legacy_draining":
                    await connection.execute("UPDATE public.ai_teacher_writer_generation_state SET state='DRAINING' WHERE generation='legacy'")
                elif case == "candidate_missing":
                    await connection.execute("DELETE FROM public.ai_teacher_writer_generation_state WHERE generation='candidate_p'")
                elif case == "candidate_not_serving":
                    await connection.execute("UPDATE public.ai_teacher_writer_generation_state SET state='FENCED' WHERE generation='candidate_p'")
                elif case == "second_admissible_generation":
                    await connection.execute("INSERT INTO public.ai_teacher_writer_generation_state(generation,database_role,state) VALUES ('old2','old2_role','SERVING')")
                elif case == "public_execute":
                    await connection.execute("GRANT EXECUTE ON FUNCTION public.gate738k_admit_writer() TO PUBLIC")
            finally:
                await connection.close()

            if case == "old_transaction":
                blocker_connection = await asyncpg.connect(
                    target_dsn, user="app_runtime",
                    server_settings={"application_name": "aitw:legacy:old1"}
                )
                await blocker_connection.execute("BEGIN")
                await blocker_connection.execute("SELECT 1")
            elif case == "candidate_spoof":
                blocker_connection = await asyncpg.connect(
                    target_dsn, user="app_runtime",
                    server_settings={"application_name": "aitw:candidate_p:spoofed"}
                )
                with pytest.raises(asyncpg.ObjectNotInPrerequisiteStateError):
                    await blocker_connection.execute("SELECT public.gate738k_admit_writer()")
            elif case == "valid_candidate":
                blocker_connection = await asyncpg.connect(
                    target_dsn, user=role,
                    server_settings={"application_name": "aitw:candidate_p:candidate1"},
                )
                await blocker_connection.execute("SELECT 1")

            if case != "valid_candidate":
                candidate_connection = await asyncpg.connect(
                    target_dsn, user=role,
                    server_settings={"application_name": "aitw:candidate_p:candidate1"},
                )
                await candidate_connection.execute("SELECT 1")

            contract = await _run_alembic(environment, "20261003_0030")
            if expected_reason:
                assert contract.returncode != 0, f"guard incorrectly accepted {case}"
                assert expected_reason in contract.stderr, f"guard refused {case} for an unexpected reason"
                check = await asyncpg.connect(target_dsn)
                try:
                    assert await check.fetchval("SELECT version_num FROM public.alembic_version") == "20261004_0032"
                    assert await check.fetchval("SELECT count(*) FROM pg_catalog.pg_constraint WHERE conname='ck_submission_current_revision'") == 0
                finally:
                    await check.close()
            else:
                assert contract.returncode == 0, "guarded contract rejected a fully eligible candidate"
        finally:
            if blocker_connection is not None:
                await blocker_connection.close()
            if candidate_connection is not None:
                await candidate_connection.close()
            await admin.execute("SELECT pg_catalog.pg_terminate_backend(pid) FROM pg_catalog.pg_stat_activity WHERE datname=$1", database)
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}"')
            await admin.execute(f'DROP ROLE IF EXISTS "{role}"')
            await admin.close()

    asyncio.run(exercise())
