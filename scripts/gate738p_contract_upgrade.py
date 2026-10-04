"""Fail-closed, explicitly staged Gate738P migration orchestration.

Allowed targets are named revisions only. Contract targets require an independently
healthy candidate and a database-owned OLD-generation drain/fence sequence.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

EXPAND_TARGET = "20261003_0029"
CONTROL_TARGET = "20261004_0032"
CONTRACT_TARGETS = {
    "20261003_0030": "20261004_0032",
    "20261003_0031": "20261003_0030",
    "20261004_0033": "20261003_0031",
}
_GENERATION = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
_ROLE = re.compile(r"^[A-Za-z0-9._-]{1,63}$")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(f"Gate738P migration runner refused: {reason}")


def _candidate_identity() -> tuple[str, str]:
    generation = os.environ.get("WRITER_GENERATION", "").strip()
    role = os.environ.get("WRITER_DATABASE_ROLE", "").strip()
    _require(bool(_GENERATION.fullmatch(generation)) and generation != "legacy",
             "WRITER_GENERATION must identify the candidate")
    _require(bool(_ROLE.fullmatch(role)) and role != "app_runtime",
             "WRITER_DATABASE_ROLE must identify a distinct candidate login role")
    return generation, role


def _candidate_ready(expected_head: str) -> None:
    url = os.environ.get("GATE738P_CANDIDATE_HEALTH_URL", "").strip()
    _require(bool(url), "GATE738P_CANDIDATE_HEALTH_URL is required")
    parsed = urlsplit(url)
    _require(parsed.scheme in {"http", "https"} and parsed.hostname is not None,
             "candidate readiness URL must be an HTTP(S) URL")
    _require(parsed.username is None and parsed.password is None and parsed.query == "" and parsed.fragment == "",
             "candidate readiness URL must not contain credentials, query, or fragment")
    _require(os.environ.get("WRITER_ADMISSION_ENABLED", "").lower() == "true",
             "candidate writer admission is not enabled")
    _candidate_identity()
    try:
        with urlopen(url, timeout=5) as response:
            status = response.status
            body = response.read(64 * 1024)
    except (OSError, URLError) as exc:
        raise RuntimeError("candidate readiness request failed") from exc
    _require(status == 200, "candidate readiness endpoint did not return HTTP 200")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("candidate readiness response was not valid JSON") from exc
    _require(payload.get("status") == "ready", "candidate is not ready")
    _require(payload.get("migration_head") == expected_head,
             "candidate is not ready at the exact required migration head")
    _require(payload.get("writer_identity_verified") is True,
             "candidate readiness did not verify its PostgreSQL login identity")


def _require_hard_crash_evidence(candidate: str) -> None:
    evidence_path = os.environ.get("GATE738P_HARD_CRASH_EVIDENCE_FILE", "").strip()
    _require(bool(evidence_path), "hard-crash evidence file is required before final contract")
    try:
        evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("hard-crash evidence file is missing or invalid") from exc
    required_true = (
        "old_container_hard_killed",
        "inflight_transaction_rolled_back",
        "fence_persisted_after_restart",
        "restarted_old_write_denied",
        "candidate_health_remained_ready",
        "candidate_write_succeeded",
    )
    _require(evidence.get("gate") == "Gate738P"
             and evidence.get("candidate_generation") == candidate
             and evidence.get("old_generation") == "legacy"
             and evidence.get("old_container_exit_code") == 137
             and all(evidence.get(key) is True for key in required_true)
             and bool(evidence.get("test_run_id"))
             and bool(evidence.get("old_container_id")),
             "hard-crash evidence does not prove every required scenario")


async def _transition(action: str, generation: str, role: str) -> None:
    from app.services.writer_admission import WriterState, transition_writer_generation

    database_url = os.environ.get("DATABASE_URL", "").strip()
    _require(bool(database_url), "DATABASE_URL is required")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            principal = await connection.scalar(text("SELECT session_user"))
            _require(principal != "app_runtime", "drain/fence requires the control-plane identity")
            candidate = (await connection.execute(text("""
                SELECT database_role, state FROM public.ai_teacher_writer_generation_state
                 WHERE generation=:generation
            """), {"generation": generation})).mappings().one_or_none()
            _require(candidate is not None and candidate["database_role"] == role
                     and candidate["state"] == "SERVING",
                     "candidate role must remain registered and SERVING")
            target = WriterState.DRAINING if action == "drain" else WriterState.FENCED
            if action == "fence":
                legacy = await connection.scalar(text("""
                    SELECT state FROM public.ai_teacher_writer_generation_state
                     WHERE generation='legacy' AND database_role='app_runtime'
                """))
                _require(legacy == WriterState.DRAINING.value,
                         "OLD generation must be durably DRAINING before fencing")
                other = await connection.scalar(text("""
                    SELECT count(*) FROM public.ai_teacher_writer_generation_state
                     WHERE generation NOT IN ('legacy', :candidate)
                       AND state IN ('SERVING','DRAINING')
                """), {"candidate": generation})
                _require(other == 0, "another writer generation is still admission-capable")
            await transition_writer_generation(
                connection, generation="legacy", target=target
            )
            if action == "fence":
                active_old = await connection.scalar(text("""
                    SELECT count(*) FROM pg_catalog.pg_stat_activity
                     WHERE datname=pg_catalog.current_database()
                       AND usename='app_runtime'
                       AND pid <> pg_catalog.pg_backend_pid()
                       AND xact_start IS NOT NULL
                """))
                _require(active_old == 0, "OLD-generation database write transaction remains active")
                state = await connection.scalar(text("""
                    SELECT state FROM public.ai_teacher_writer_generation_state
                     WHERE generation='legacy'
                """))
                _require(state == WriterState.FENCED.value, "OLD fence was not persisted")
    finally:
        await engine.dispose()


def _run_alembic(target: str) -> int:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "alembic", "upgrade", target],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        output = output.replace(database_url, "[DATABASE_URL REDACTED]")
    output = re.sub(
        r"(?i)(postgres(?:ql)?(?:\+[a-z0-9_]+)?://)[^\s'\"]+",
        r"\1[REDACTED]",
        output,
    )
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    return result.returncode


def main() -> int:
    target = os.environ.get("EXPECTED_MIGRATION_HEAD", "").strip()
    action = os.environ.get("GATE738P_ACTION", "").strip().lower()
    _require(target in {EXPAND_TARGET, CONTROL_TARGET, *CONTRACT_TARGETS},
             "EXPECTED_MIGRATION_HEAD must be one explicit qualified target")
    _require(action in {"", "drain", "fence"}, "GATE738P_ACTION must be drain or fence")
    _require(bool(os.environ.get("DATABASE_URL", "").strip()), "DATABASE_URL is required")
    if action:
        generation, role = _candidate_identity()
        _require(target == CONTROL_TARGET, "drain/fence actions are allowed only at the control-plane head")
        _candidate_ready(CONTROL_TARGET)
        asyncio.run(_transition(action, generation, role))
        print(f"Gate738P {action}: PASS; candidate ready; OLD generation transition persisted")
        return 0

    if target == EXPAND_TARGET:
        return _run_alembic(EXPAND_TARGET)
    generation, role = _candidate_identity()
    if target == CONTROL_TARGET:
        _require(_run_alembic(CONTROL_TARGET) == 0, "control-plane migration failed")
        return 0

    expected_head = CONTRACT_TARGETS[target]
    _candidate_ready(expected_head)
    if target == "20261004_0033":
        _require_hard_crash_evidence(generation)
    return _run_alembic(target)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
