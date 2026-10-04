"""End-to-end hard-crash proof on an explicitly named disposable PostgreSQL.

Requires GATE738P_ADMIN_URL to point to the local Gate738P PostgreSQL container.
Creates and removes one uniquely named disposable database and one candidate role.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen
from uuid import uuid4

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
IMAGE = "codex-gate738p-candidate-20261004"
EVIDENCE = ROOT / "docs" / "GATE738P_HARD_CRASH_EVIDENCE.json"
ADMIN_DSN = os.environ.get("GATE738P_ADMIN_URL", "").strip()


def _target_dsn(database: str, *, sqlalchemy: bool = False) -> str:
    parsed = urlsplit(ADMIN_DSN)
    path = f"/{database}"
    scheme = "postgresql+asyncpg" if sqlalchemy else "postgresql"
    return urlunsplit((scheme, parsed.netloc, path, "", ""))


def _run(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 180) -> str:
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True,
                            timeout=timeout, check=False)
    output = (result.stdout or "") + (result.stderr or "")
    if env and env.get("DATABASE_URL"):
        output = output.replace(env["DATABASE_URL"], "[DATABASE_URL REDACTED]")
    if result.returncode:
        raise RuntimeError(f"command failed ({args[0]}): {output[-5000:]}")
    return output


def _migration_env(database_url: str, target: str, generation: str = "", role: str = "",
                   action: str = "", health_url: str = "") -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": database_url,
        "EXPECTED_MIGRATION_HEAD": target,
        "WRITER_GENERATION": generation,
        "WRITER_DATABASE_ROLE": role,
        "WRITER_ADMISSION_ENABLED": "true" if generation else "false",
        "GATE738P_ACTION": action,
        "GATE738P_CANDIDATE_HEALTH_URL": health_url,
    })
    env.pop("GATE738P_HARD_CRASH_EVIDENCE_FILE", None)
    return env


def _migration(database_url: str, target: str, *, generation: str = "", role: str = "",
               action: str = "", health_url: str = "") -> None:
    _run(
        [sys.executable, "-B", "-m", "scripts.gate738p_contract_upgrade"],
        env=_migration_env(database_url, target, generation, role, action, health_url),
        timeout=300,
    )


def _docker(args: list[str], *, timeout: int = 180) -> str:
    return _run(["docker", *args], timeout=timeout).strip()


def _ready(url: str, *, attempts: int = 80) -> dict[str, object]:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    payload = json.loads(response.read(64 * 1024))
                    if (payload.get("status") == "ready"
                            and payload.get("writer_identity_verified") is True):
                        return payload
        except (OSError, URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"candidate readiness did not pass: {type(last_error).__name__ if last_error else 'invalid response'}")


def _logs_contain(container: str, marker: str, attempts: int = 80) -> str:
    for _ in range(attempts):
        logs = _docker(["logs", container], timeout=15)
        if marker in logs:
            return logs
        state = json.loads(_docker(["inspect", "--format", "{{json .State}}", container]))
        if not state.get("Running"):
            raise RuntimeError(f"disposable writer exited before {marker}; exit={state.get('ExitCode')}; logs={logs[-2000:]}")
        time.sleep(0.25)
    raise RuntimeError(f"disposable writer did not report {marker}")


def _start_candidate(name: str, database: str, role: str, generation: str,
                     expected_head: str) -> str:
    database_url = f"postgresql+asyncpg://{role}@host.docker.internal:{urlsplit(ADMIN_DSN).port}/{database}"
    _docker([
        "run", "--detach", "--name", name,
        "--label", "codex.gate=738p", "--label", "codex.scope=disposable",
        "--add-host", "host.docker.internal:host-gateway",
        "--publish", "127.0.0.1::8000",
        "--env", f"DATABASE_URL={database_url}",
        "--env", "APP_ENV=development",
        "--env", "WRITER_ADMISSION_ENABLED=true",
        "--env", f"WRITER_GENERATION={generation}",
        "--env", "WRITER_INSTANCE_ID=candidate1",
        "--env", f"WRITER_DATABASE_ROLE={role}",
        "--env", f"EXPECTED_MIGRATION_HEAD={expected_head}",
        IMAGE,
    ])
    port = _docker([
        "inspect", "--format",
        '{{range (index .NetworkSettings.Ports "8000/tcp")}}{{.HostPort}}{{end}}', name,
    ])
    if not port.isdigit():
        raise RuntimeError("candidate API did not receive a loopback port")
    return f"http://127.0.0.1:{port}/health/ready"


def _start_writer(name: str, mode: str, database: str, role: str,
                  generation: str, user_id: int, write_value: str) -> str:
    scheme = "postgresql+asyncpg" if mode == "candidate-write" else "postgresql"
    database_url = f"{scheme}://{role}@host.docker.internal:{urlsplit(ADMIN_DSN).port}/{database}"
    _docker([
        "run", "--detach", "--name", name,
        "--label", "codex.gate=738p", "--label", "codex.scope=disposable",
        "--add-host", "host.docker.internal:host-gateway",
        "--env", f"DATABASE_URL={database_url}",
        "--env", f"GATE738P_CRASH_MODE={mode}",
        "--env", f"GATE738P_USER_ID={user_id}",
        "--env", f"GATE738P_WRITE_VALUE={write_value}",
        "--env", f"WRITER_GENERATION={generation}",
        "--env", "WRITER_INSTANCE_ID=candidate1",
        "--env", f"WRITER_DATABASE_ROLE={role}",
        "--entrypoint", "python",
        IMAGE, "scripts/gate738p_crash_writer.py",
    ])
    return name


async def _wait_for_drain_lock(admin: asyncpg.Connection, database: str, process: subprocess.Popen[str]) -> None:
    for _ in range(200):
        if process.poll() is not None:
            stdout, stderr = await asyncio.to_thread(process.communicate)
            raise RuntimeError(f"drain exited before waiting for the OLD transaction: {(stdout + stderr)[-3000:]}")
        waiting = await admin.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_catalog.pg_stat_activity
                 WHERE datname=$1 AND usename='postgres'
                   AND wait_event_type='Lock' AND pid <> pg_catalog.pg_backend_pid()
            )
        """, database)
        if waiting:
            return
        await asyncio.sleep(0.1)
    raise RuntimeError("did not observe the drain process waiting on the in-flight OLD transaction")


async def _candidate_write(database: str, role: str, generation: str, user_id: int, value: str) -> None:
    from sqlalchemy import text

    from app.db.base import build_session_factory, dispose_session_factory

    database_url = f"postgresql+asyncpg://{role}@127.0.0.1:{urlsplit(ADMIN_DSN).port}/{database}"
    factory = build_session_factory(database_url, True, generation, "candidate1", role)
    try:
        async with factory() as session, session.begin():
            result = await session.execute(
                text("UPDATE public.users SET username=:value WHERE id=:user_id"),
                {"value": value, "user_id": user_id},
            )
            if result.rowcount != 1:
                raise RuntimeError("candidate synthetic row update did not affect exactly one row")
    finally:
        await dispose_session_factory(factory)


async def qualify() -> dict[str, object]:
    if not ADMIN_DSN:
        raise RuntimeError("GATE738P_ADMIN_URL must identify the local disposable Gate738P PostgreSQL")
    parsed = urlsplit(ADMIN_DSN)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or not parsed.port:
        raise RuntimeError("Gate738P qualification is restricted to a loopback PostgreSQL endpoint")
    database = "gate738e_gate738p_" + uuid4().hex[:10]
    candidate_role = "gpc_" + uuid4().hex[:12]
    generation = "candidate_" + uuid4().hex[:10]
    name_token = uuid4().hex[:8]
    api_name = f"codex-gate738p-api-{name_token}"
    old_name = f"codex-gate738p-old-{name_token}"
    drain_process: subprocess.Popen[str] | None = None
    admin = await asyncpg.connect(ADMIN_DSN)
    database_url = _target_dsn(database, sqlalchemy=True)
    try:
        if not await admin.fetchval("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='app_runtime'"):
            raise RuntimeError("isolated Gate738P PostgreSQL is missing its app_runtime role")
        await admin.execute(f'CREATE DATABASE "{database}"')
        await admin.execute(f'CREATE ROLE "{candidate_role}" LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION')
        await admin.execute(f'GRANT app_runtime TO "{candidate_role}"')

        _migration(database_url, "20261003_0029")
        # This isolated synthetic database has no user-submission rows. The
        # real bounded validator establishes an empty, zero-error backfill.
        backfill_env = os.environ.copy()
        backfill_env.update({"DATABASE_URL": database_url, "GATE738E_DISPOSABLE": "1"})
        _run([sys.executable, "-B", "scripts/backfill_submission_revisions.py"], env=backfill_env)

        db = await asyncpg.connect(_target_dsn(database))
        try:
            await db.execute("GRANT SELECT, INSERT, UPDATE ON TABLE public.users TO app_runtime")
            await db.execute("GRANT USAGE, SELECT ON SEQUENCE public.users_id_seq TO app_runtime")
            username = "gate738p_before_" + name_token
            user_id = await db.fetchval(
                "INSERT INTO public.users(username,role) VALUES($1,'STUDENT') RETURNING id", username
            )
        finally:
            await db.close()
        _migration(database_url, "20261004_0032", generation=generation, role=candidate_role)

        health_url = _start_candidate(api_name, database, candidate_role, generation, "20261004_0032")
        _ready(health_url)
        crash_value = "gate738p_uncommitted_" + name_token
        _start_writer(old_name, "hold", database, "app_runtime", "legacy", int(user_id), crash_value)
        _logs_contain(old_name, "TX_READY")

        drain_env = _migration_env(database_url, "20261004_0032", generation, candidate_role,
                                   "drain", health_url)
        drain_process = await asyncio.to_thread(
            subprocess.Popen,
            [sys.executable, "-B", "-m", "scripts.gate738p_contract_upgrade"],
            cwd=ROOT, env=drain_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        await _wait_for_drain_lock(admin, database, drain_process)
        _docker(["kill", old_name])
        exited = json.loads(_docker(["inspect", "--format", "{{json .State}}", old_name]))
        if exited.get("ExitCode") != 137:
            raise RuntimeError(f"OLD container was not hard-killed with exit 137; observed {exited.get('ExitCode')}")
        try:
            stdout, stderr = await asyncio.to_thread(drain_process.communicate, timeout=45)
        except subprocess.TimeoutExpired as exc:
            drain_process.kill()
            raise RuntimeError("drain did not finish after the OLD transaction was killed") from exc
        if drain_process.returncode != 0:
            raise RuntimeError(f"drain action failed: {(stdout + stderr)[-3000:]}")

        db = await asyncpg.connect(_target_dsn(database))
        try:
            old_after_crash = await db.fetchval("SELECT username FROM public.users WHERE id=$1", int(user_id))
            state = await db.fetchval("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation='legacy'")
            if old_after_crash != username or state != "DRAINING":
                raise RuntimeError("hard crash did not roll back the in-flight write and complete the durable drain")
        finally:
            await db.close()

        old_restart = f"codex-gate738p-old-restart-{name_token}"
        _start_writer(old_restart, "old-write", database, "app_runtime", "legacy", int(user_id), "old_restart_denied")
        _logs_contain(old_restart, "OLD_WRITE_DENIED")
        _migration(database_url, "20261004_0032", generation=generation, role=candidate_role,
                   action="fence", health_url=health_url)
        db = await asyncpg.connect(_target_dsn(database))
        try:
            fenced = await db.fetchval("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation='legacy'")
        finally:
            await db.close()
        if fenced != "FENCED":
            raise RuntimeError("the OLD generation was not persistently fenced")

        old_restart_after_fence = f"codex-gate738p-old-fenced-restart-{name_token}"
        _start_writer(old_restart_after_fence, "old-write", database, "app_runtime", "legacy", int(user_id), "old_fenced_denied")
        _logs_contain(old_restart_after_fence, "OLD_WRITE_DENIED")
        health_after_crash = _ready(health_url)
        await _candidate_write(database, candidate_role, generation, int(user_id),
                               "candidate_committed_" + name_token)

        evidence: dict[str, object] = {
            "gate": "Gate738P",
            "test_run_id": name_token,
            "database": database,
            "candidate_generation": generation,
            "old_generation": "legacy",
            "old_container_id": _docker(["inspect", "--format", "{{.Id}}", old_name]),
            "old_container_exit_code": 137,
            "old_container_hard_killed": True,
            "inflight_transaction_rolled_back": old_after_crash == username,
            "fence_persisted_after_restart": fenced == "FENCED",
            "restarted_old_write_denied": True,
            "candidate_health_remained_ready": (
                health_after_crash.get("status") == "ready"
                and health_after_crash.get("writer_identity_verified") is True
            ),
            "candidate_write_succeeded": True,
        }
        if not all(value is True for key, value in evidence.items() if key.endswith(("rolled_back", "persisted_after_restart", "denied", "remained_ready", "succeeded"))):
            raise RuntimeError("hard-crash qualification evidence did not satisfy every required assertion")
        EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

        # Exercise every explicit contract target only after crash/fence proof.
        _migration(database_url, "20261003_0030", generation=generation, role=candidate_role,
                   health_url=health_url)
        _docker(["rm", "--force", api_name])
        health_url = _start_candidate(api_name, database, candidate_role, generation, "20261003_0030")
        _ready(health_url)
        _migration(database_url, "20261003_0031", generation=generation, role=candidate_role,
                   health_url=health_url)
        _docker(["rm", "--force", api_name])
        health_url = _start_candidate(api_name, database, candidate_role, generation, "20261003_0031")
        _ready(health_url)
        final_env = _migration_env(database_url, "20261004_0033", generation, candidate_role,
                                   health_url=health_url)
        final_env["GATE738P_HARD_CRASH_EVIDENCE_FILE"] = str(EVIDENCE)
        _run([sys.executable, "-B", "-m", "scripts.gate738p_contract_upgrade"], env=final_env)
        _docker(["rm", "--force", api_name])
        health_url = _start_candidate(api_name, database, candidate_role, generation, "20261004_0033")
        _ready(health_url)
        db = await asyncpg.connect(_target_dsn(database))
        try:
            final_head = await db.fetchval("SELECT version_num FROM public.alembic_version")
            legacy_state = await db.fetchval("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation='legacy'")
            candidate_state = await db.fetchval("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation=$1", generation)
            contracted = await db.fetchval("SELECT status FROM public.submission_revision_backfill_state WHERE singleton=true")
            constraint_count = await db.fetchval("SELECT count(*) FROM pg_catalog.pg_constraint WHERE conname='ck_submission_current_revision'")
        finally:
            await db.close()
        if (final_head != "20261004_0033" or legacy_state != "FENCED"
                or candidate_state != "SERVING" or contracted != "CONTRACTED" or constraint_count != 1):
            raise RuntimeError("final explicit contract state did not match the expected qualified shape")
        evidence["contract_targets"] = ["20261003_0030", "20261003_0031", "20261004_0033"]
        evidence["final_head"] = final_head
        evidence["final_candidate_health_ready"] = True
        EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2))
        return evidence
    finally:
        if drain_process is not None and drain_process.poll() is None:
            drain_process.kill()
            await asyncio.to_thread(drain_process.communicate)
        for name in (api_name, old_name, f"codex-gate738p-old-restart-{name_token}",
                     f"codex-gate738p-old-fenced-restart-{name_token}"):
            await asyncio.to_thread(
                subprocess.run, ["docker", "rm", "--force", name],
                capture_output=True, text=True, check=False,
            )
        try:
            await admin.execute(
                "SELECT pg_catalog.pg_terminate_backend(pid) FROM pg_catalog.pg_stat_activity WHERE datname=$1",
                database,
            )
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}"')
            await admin.execute(f'DROP ROLE IF EXISTS "{candidate_role}"')
        finally:
            await admin.close()


if __name__ == "__main__":
    asyncio.run(qualify())
