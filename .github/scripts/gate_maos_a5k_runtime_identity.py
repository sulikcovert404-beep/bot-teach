"""Provision and verify the runtime identity only in disposable staging-smoke CI."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


class GateError(RuntimeError):
    """A redacted, safe-to-report GateMAOS-A5K failure."""


_COMPOSE_CONFIG = ["docker", "compose", "config", "--format", "json"]
_PSQL = [
    "docker",
    "compose",
    "exec",
    "-T",
    "db",
    "psql",
    "-X",
    "-U",
    "postgres",
    "-w",
    "-d",
    "education",
    "-A",
    "-t",
    "-v",
    "ON_ERROR_STOP=1",
]
_ROLE_ATTRIBUTES = "1|1|0|0|0|0|0"
_REVISION = re.compile(r"\A[0-9]{8}_[0-9]{4}\Z")
_SQLSTATE = re.compile(r"\A[0-9A-Z]{5}\Z")

_PRE_API_PROBE = r'''import asyncio
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

REVISION = re.compile(r"\A[0-9]{8}_[0-9]{4}\Z")
SQLSTATE = re.compile(r"\A[0-9A-Z]{5}\Z")

def safe_sqlstate(error):
    original = getattr(error, "orig", error)
    value = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    return value if isinstance(value, str) and SQLSTATE.fullmatch(value) else "UNKNOWN"

async def main():
    engine = None
    try:
        engine = create_async_engine(get_settings().database_url, echo=False)
        async with engine.connect() as connection:
            identity = (await connection.execute(text(
                "SELECT session_user, current_user, current_database()"
            ))).one()
            if tuple(identity) != ("app_runtime", "app_runtime", "education"):
                print("A5K_RUNTIME_IDENTITY=FAIL")
                return 21
            print("A5K_RUNTIME_IDENTITY=PASS")
            try:
                revision = (await connection.execute(text(
                    "SELECT version_num FROM public.alembic_version"
                ))).scalar_one_or_none()
            except Exception as error:
                print("A5K_ALEMBIC_VERSION_READ=FAIL SQLSTATE=" + safe_sqlstate(error))
                return 22
            if not isinstance(revision, str) or not REVISION.fullmatch(revision):
                print("A5K_ALEMBIC_VERSION_READ=FAIL SQLSTATE=UNKNOWN")
                return 23
            print("A5K_ALEMBIC_VERSION_READ=PASS REVISION=" + revision)
            return 0
    except Exception as error:
        print("A5K_RUNTIME_IDENTITY=FAIL SQLSTATE=" + safe_sqlstate(error))
        return 24
    finally:
        if engine is not None:
            try:
                await engine.dispose()
            except Exception:
                pass

raise SystemExit(asyncio.run(main()))
'''


def _run(
    args: list[str], *, input_text: str | None = None, timeout: int = 20
) -> subprocess.CompletedProcess[str]:
    """Run a fixed local Compose command without surfacing command or stderr data."""
    try:
        return subprocess.run(
            args,
            input=input_text,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        raise GateError("COMPOSE_COMMAND_FAILED") from None


def _runtime_database_url(config_text: str) -> str:
    """Extract the resolved API URL without emitting the secret-bearing config."""
    try:
        config = json.loads(config_text)
        value = config["services"]["api"]["environment"]["DATABASE_URL"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise GateError("API_DATABASE_CONFIGURATION_UNAVAILABLE") from None
    if not isinstance(value, str):
        raise GateError("API_DATABASE_CONFIGURATION_UNAVAILABLE")
    return value


def _runtime_credential(database_url: str) -> str:
    """Require the exact disposable API runtime endpoint and return its password."""
    try:
        parsed = urlsplit(database_url)
        password = unquote(parsed.password or "")
        port = parsed.port
    except ValueError:
        raise GateError("API_DATABASE_TARGET_INVALID") from None
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname != "db"
        or port != 5432
        or parsed.username != "app_runtime"
        or parsed.path != "/education"
        or parsed.query
        or parsed.fragment
        or not password
        or any(ord(char) < 32 or ord(char) == 127 for char in password)
    ):
        raise GateError("API_DATABASE_TARGET_INVALID")
    return password


def _compose_runtime_password() -> str:
    result = _run(_COMPOSE_CONFIG)
    if result.returncode != 0:
        raise GateError("API_DATABASE_CONFIGURATION_UNAVAILABLE")
    return _runtime_credential(_runtime_database_url(result.stdout))


def _password_sql_literal(password: str) -> str:
    """Encode a password as an escaped PostgreSQL E-string literal."""
    if any(ord(char) < 32 or ord(char) == 127 for char in password):
        raise GateError("API_RUNTIME_CREDENTIAL_INVALID")
    escaped = password.replace("\\", "\\\\").replace("'", "\\'")
    return "E'" + escaped + "'"


def _psql(sql: str) -> str:
    result = _run(_PSQL, input_text=sql, timeout=20)
    if result.returncode != 0:
        raise GateError("DISPOSABLE_ROLE_BOOTSTRAP_FAILED")
    return result.stdout.strip()


def bootstrap_role(password: str) -> None:
    """Create only a least-privilege app_runtime login in the disposable DB."""
    present = _psql(
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_catalog.pg_roles "
        "WHERE rolname = 'app_runtime') THEN 'present' ELSE 'absent' END;"
    )
    if present == "present":
        raise GateError("APP_RUNTIME_ROLE_ALREADY_PRESENT")
    if present != "absent":
        raise GateError("ROLE_PRESENCE_CHECK_FAILED")

    password_literal = _password_sql_literal(password)
    _psql(
        "CREATE ROLE app_runtime LOGIN "
        f"PASSWORD {password_literal} "
        "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"
    )
    attributes = _psql(
        "SELECT (CASE WHEN rolcanlogin THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolinherit THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolsuper THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolcreatedb THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolcreaterole THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolreplication THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolbypassrls THEN '1' ELSE '0' END) "
        "FROM pg_catalog.pg_roles "
        "WHERE rolname = 'app_runtime';"
    )
    if attributes != _ROLE_ATTRIBUTES:
        raise GateError("APP_RUNTIME_ROLE_ATTRIBUTES_MISMATCH")


def pre_api_check() -> None:
    """Use the API service's actual environment for the read-only DB contract check."""
    result = _run(
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "--build",
            "--entrypoint",
            "python",
            "api",
            "-B",
            "-c",
            _PRE_API_PROBE,
        ],
        timeout=180,
    )
    safe_lines = []
    for line in result.stdout.splitlines():
        if line == "A5K_RUNTIME_IDENTITY=PASS":
            safe_lines.append(line)
        elif line.startswith("A5K_RUNTIME_IDENTITY=FAIL SQLSTATE="):
            code = line.rsplit("=", 1)[-1]
            safe_lines.append(
                "A5K_RUNTIME_IDENTITY=FAIL SQLSTATE="
                + (code if _SQLSTATE.fullmatch(code) else "UNKNOWN")
            )
        elif line.startswith("A5K_ALEMBIC_VERSION_READ=FAIL SQLSTATE="):
            code = line.rsplit("=", 1)[-1]
            safe_lines.append(
                "A5K_ALEMBIC_VERSION_READ=FAIL SQLSTATE="
                + (code if _SQLSTATE.fullmatch(code) else "UNKNOWN")
            )
        elif line.startswith("A5K_ALEMBIC_VERSION_READ=PASS REVISION="):
            revision = line.rsplit("=", 1)[-1]
            if _REVISION.fullmatch(revision):
                safe_lines.append("A5K_ALEMBIC_VERSION_READ=PASS REVISION=" + revision)

    for line in safe_lines:
        print(line)
    if result.returncode != 0:
        if any(line.startswith("A5K_ALEMBIC_VERSION_READ=FAIL") for line in safe_lines):
            raise GateError("APP_RUNTIME_ALEMBIC_VERSION_PRIVILEGE_OR_READ_FAILED")
        if any(line.startswith("A5K_RUNTIME_IDENTITY=FAIL") for line in safe_lines):
            raise GateError("APP_RUNTIME_CONNECTION_OR_IDENTITY_FAILED")
        raise GateError("PRE_API_RUNTIME_CHECK_FAILED")
    if not any(line.startswith("A5K_RUNTIME_IDENTITY=PASS") for line in safe_lines):
        raise GateError("PRE_API_RUNTIME_IDENTITY_EVIDENCE_MISSING")
    if not any(line.startswith("A5K_ALEMBIC_VERSION_READ=PASS") for line in safe_lines):
        raise GateError("PRE_API_ALEMBIC_VERSION_EVIDENCE_MISSING")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["bootstrap-role"]:
        try:
            bootstrap_role(_compose_runtime_password())
        except GateError as error:
            print("GATE_MAOS_A5K_BLOCKED=" + str(error))
            return 1
        print("GATE_MAOS_A5K_BOOTSTRAP=PASS ROLE=app_runtime")
        return 0
    if arguments == ["pre-api-check"]:
        try:
            pre_api_check()
        except GateError as error:
            print("GATE_MAOS_A5K_BLOCKED=" + str(error))
            return 1
        print("GATE_MAOS_A5K_PRE_API_CHECK=PASS")
        return 0
    print("GATE_MAOS_A5K_BLOCKED=INVALID_COMMAND")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
