#!/usr/bin/env python3
"""Emit allowlisted diagnostics for the disposable GateMAOS-A5I CI stack."""
from __future__ import annotations

import json
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_HEAD = re.compile(r"\A\d{8}_\d{4}\Z")
_HEAD_LIST = re.compile(r"\A\d{8}_\d{4}(?:,\d{8}_\d{4})*\Z")
_IDENT = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SERVICES = {"api", "db", "redis", "migrate"}
_STATES = {"created", "running", "restarting", "paused", "exited", "removing"}
_HEALTH = {"healthy", "unhealthy", "starting", "none"}
_DETAIL_CODES = {
    "Database unavailable": "DATABASE_UNAVAILABLE",
    "Migration drift / Not ready": "MIGRATION_HEAD_MISMATCH",
    "Writer database role mismatch": "WRITER_ROLE_MISMATCH",
}


def safe_head(value: object) -> str:
    if not isinstance(value, str):
        return "NOT_AVAILABLE"
    value = value.strip()
    return value if _HEAD.fullmatch(value) else "NOT_AVAILABLE"


def safe_revision_list(value: object) -> str:
    if not isinstance(value, str):
        return "NOT_AVAILABLE"
    value = value.strip()
    if not value:
        return "NO_ROWS"
    return value if _HEAD_LIST.fullmatch(value) else "NOT_AVAILABLE"


def readiness_fields(status: int | None, body: bytes) -> tuple[str, str]:
    """Return only a fixed reason code and a validated migration revision."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return "UNKNOWN", "NOT_AVAILABLE"
    if not isinstance(payload, dict):
        return "UNKNOWN", "NOT_AVAILABLE"
    if status == 200 and payload.get("status") == "ready":
        reason = "READY"
    else:
        detail = payload.get("detail")
        reason = _DETAIL_CODES.get(detail, "UNKNOWN") if isinstance(detail, str) else "UNKNOWN"
    return reason, safe_head(payload.get("migration_head"))


def safe_db_identity(value: object) -> str:
    if not isinstance(value, str):
        return "NOT_AVAILABLE"
    parts = value.strip().split("|")
    if len(parts) != 4 or not all(_IDENT.fullmatch(part) for part in parts):
        return "NOT_AVAILABLE"
    return "|".join(parts)


def _run(args: list[str], timeout: int = 12) -> str | None:
    """Run a fixed diagnostic command; never surface stderr or command details."""
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _readiness_probe() -> tuple[str, str, str]:
    try:
        with urlopen(Request("http://localhost:8000/health/ready"), timeout=5) as response:
            status = response.status
            body = response.read(8192)
    except HTTPError as exc:
        status = exc.code
        try:
            body = exc.read(8192)
        except (OSError, URLError, TimeoutError):
            body = b""
    except (OSError, URLError, TimeoutError, ValueError):
        return "TRANSPORT_ERROR", "NOT_AVAILABLE", "NOT_AVAILABLE"
    reason, revision = readiness_fields(status, body)
    return str(status), reason, revision


def _container_health() -> list[tuple[str, str, str]]:
    raw = _run(["docker", "compose", "ps", "--all", "--format", "json"])
    if raw is None:
        return []
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        rows = []
        for line in raw.splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                return []
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return []
    result: list[tuple[str, str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        service = row.get("Service", row.get("service", ""))
        if not isinstance(service, str) or service not in _SERVICES:
            continue
        state = str(row.get("State", row.get("state", ""))).split()[0].lower()
        health = str(row.get("Health", row.get("health", ""))).lower()
        if state not in _STATES:
            state = "unknown"
        if health not in _HEALTH:
            health = "not_available"
        result.append((service, state, health))
    return sorted(result)


def _effective_expected_head() -> str:
    code = (
        "from app.api.routes.health import EXPECTED_MIGRATION_HEAD; "
        "from app.core.config import get_settings; "
        "settings = get_settings(); "
        "print(settings.expected_migration_head.strip() or EXPECTED_MIGRATION_HEAD)"
    )
    return safe_head(
        _run(["docker", "compose", "exec", "-T", "api", "python", "-c", code])
    )


def _api_database_diagnostics() -> tuple[str, str]:
    code = """import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    identity_value = "NOT_AVAILABLE"
    revision_value = "NOT_AVAILABLE"
    try:
        async with engine.connect() as connection:
            try:
                identity = await connection.execute(text(
                    "SELECT current_database() || chr(124) || current_schema() || chr(124) "
                    "|| session_user || chr(124) || current_user"
                ))
                identity_value = str(identity.scalar_one())
            except Exception:
                pass
            try:
                revision = await connection.execute(text(
                    "SELECT string_agg(version_num, chr(44)) FROM public.alembic_version"
                ))
                revision_value = revision.scalar_one_or_none() or "NO_ROWS"
            except Exception:
                pass
    finally:
        await engine.dispose()
    print("A5I_DB_IDENTITY=" + identity_value)
    print("A5I_OBSERVED_ALEMBIC_REVISION=" + revision_value)

asyncio.run(main())
"""
    output = _run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
        timeout=15,
    )
    fields: dict[str, str] = {}
    if output:
        for line in output.splitlines():
            key, separator, value = line.partition("=")
            if separator and key in {"A5I_DB_IDENTITY", "A5I_OBSERVED_ALEMBIC_REVISION"}:
                fields[key] = value
    identity = safe_db_identity(fields.get("A5I_DB_IDENTITY"))
    revision = safe_revision_list(fields.get("A5I_OBSERVED_ALEMBIC_REVISION"))
    return identity, revision


def _redis_ping() -> str:
    code = """from app.core.config import get_settings
from redis import Redis

url = get_settings().redis_url.strip()
if not url:
    print("NOT_CONFIGURED")
else:
    client = Redis.from_url(url)
    try:
        client.ping()
        print("PASS")
    except Exception:
        print("FAIL")
    finally:
        try:
            client.close()
        except Exception:
            pass
"""
    result = _run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
        timeout=8,
    )
    return result if result in {"PASS", "FAIL", "NOT_CONFIGURED"} else "NOT_AVAILABLE"


def main() -> None:
    status, reason, response_head = _readiness_probe()
    print(f"A5I_HTTP_STATUS={status}")
    print(f"A5I_READINESS_REASON={reason}")
    print(f"A5I_READINESS_RESPONSE_HEAD={response_head}")
    print(f"A5I_EFFECTIVE_EXPECTED_HEAD={_effective_expected_head()}")

    identity, revision = _api_database_diagnostics()
    print(f"A5I_DB_IDENTITY={identity}")
    print(f"A5I_OBSERVED_ALEMBIC_REVISION={revision}")
    print(f"A5I_REDIS_PING={_redis_ping()}")

    health = _container_health()
    if health:
        for service, state, result in health:
            print(f"A5I_CONTAINER_{service.upper()}_STATE={state}")
            print(f"A5I_CONTAINER_{service.upper()}_HEALTH={result}")
    else:
        print("A5I_CONTAINER_HEALTH=NOT_AVAILABLE")


if __name__ == "__main__":
    main()
