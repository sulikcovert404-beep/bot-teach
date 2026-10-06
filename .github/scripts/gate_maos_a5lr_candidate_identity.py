"""Provision and verify GateMAOS-A5L-R's disposable migration candidate role."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path


class GateError(RuntimeError):
    """A fail-closed, redacted disposable candidate bootstrap error."""


ROOT = Path(__file__).resolve().parents[2]
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_CONTAINER_ID = re.compile(r"\A[0-9a-f]{64}\Z")
_RUN_NUMBER = re.compile(r"\A[1-9][0-9]{0,19}\Z")
_ROLE = re.compile(r"\Aa5lr_[1-9][0-9]{0,19}_[1-9][0-9]{0,5}\Z")
_GENERATION = re.compile(r"\Aci_a5lr_[1-9][0-9]{0,19}_[1-9][0-9]{0,5}\Z")
_CANDIDATE_ATTRIBUTES = "1|1|0|0|0|0|0"
_RUNTIME_ATTRIBUTES = "1|1|0|0|0|0|0"

_PSQL = [
    "docker",
    "compose",
    "exec",
    "-T",
    "db",
    "psql",
    "-X",
    "-q",
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


def _run(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            input=input_text,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        raise GateError("DISPOSABLE_COMPOSE_COMMAND_FAILED") from None


def _ci_identity() -> tuple[str, str]:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise GateError("GITHUB_ACTIONS_REQUIRED")
    workspace = os.environ.get("GITHUB_WORKSPACE", "")
    source_sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    output_path = os.environ.get("GITHUB_OUTPUT", "")
    if (
        not workspace
        or Path(workspace).resolve() != ROOT.resolve()
        or not _SHA.fullmatch(source_sha)
        or not _RUN_NUMBER.fullmatch(run_id)
        or not _RUN_NUMBER.fullmatch(attempt)
        or not output_path
    ):
        raise GateError("DISPOSABLE_CI_IDENTITY_INVALID")

    head = _run(["git", "rev-parse", "HEAD"])
    if head.returncode != 0 or head.stdout.strip() != source_sha:
        raise GateError("DISPOSABLE_CI_CHECKOUT_MISMATCH")

    containers = _run(["docker", "compose", "ps", "-q", "db"])
    container_id = containers.stdout.strip()
    if containers.returncode != 0 or not _CONTAINER_ID.fullmatch(container_id):
        raise GateError("DISPOSABLE_COMPOSE_DATABASE_UNAVAILABLE")

    inspected = _run(["docker", "inspect", "--format", "{{json .Config.Labels}}", container_id])
    if inspected.returncode != 0:
        raise GateError("DISPOSABLE_COMPOSE_DATABASE_ATTESTATION_FAILED")
    try:
        labels = json.loads(inspected.stdout)
    except (json.JSONDecodeError, TypeError):
        raise GateError("DISPOSABLE_COMPOSE_DATABASE_ATTESTATION_FAILED") from None
    if not isinstance(labels, dict):
        raise GateError("DISPOSABLE_COMPOSE_DATABASE_ATTESTATION_FAILED")
    working_dir = labels.get("com.docker.compose.project.working_dir")
    config_files = labels.get("com.docker.compose.project.config_files")
    configs = config_files.split(",") if isinstance(config_files, str) else []
    expected_compose = (ROOT / "docker-compose.yml").resolve()
    if (
        labels.get("com.docker.compose.service") != "db"
        or not isinstance(working_dir, str)
        or Path(working_dir).resolve() != ROOT.resolve()
        or not any(
            isinstance(path, str) and Path(path).resolve() == expected_compose for path in configs
        )
    ):
        raise GateError("DISPOSABLE_COMPOSE_DATABASE_ATTESTATION_FAILED")

    role = f"a5lr_{run_id}_{attempt}"
    generation = f"ci_a5lr_{run_id}_{attempt}"
    if not _ROLE.fullmatch(role) or not _GENERATION.fullmatch(generation):
        raise GateError("DISPOSABLE_CANDIDATE_ID_INVALID")
    return role, generation


def _psql(sql: str) -> str:
    result = _run(_PSQL, input_text=sql)
    if result.returncode != 0:
        raise GateError("DISPOSABLE_CANDIDATE_SQL_FAILED")
    return result.stdout.strip()


def _role_attributes(role: str) -> str:
    if role != "app_runtime" and not _ROLE.fullmatch(role):
        raise GateError("DISPOSABLE_CANDIDATE_ID_INVALID")
    return _psql(
        "SELECT (CASE WHEN rolcanlogin THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolinherit THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolsuper THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolcreatedb THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolcreaterole THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolreplication THEN '1' ELSE '0' END) || '|' || "
        "(CASE WHEN rolbypassrls THEN '1' ELSE '0' END) "
        "FROM pg_catalog.pg_roles WHERE rolname = '" + role + "';"
    )


def _write_outputs(role: str, generation: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT", "")
    if not output_path:
        raise GateError("GITHUB_OUTPUT_UNAVAILABLE")
    try:
        with Path(output_path).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"writer_role={role}\nwriter_generation={generation}\n")
    except OSError:
        raise GateError("GITHUB_OUTPUT_WRITE_FAILED") from None


def bootstrap_candidate() -> tuple[str, str]:
    role, generation = _ci_identity()
    credential = secrets.token_urlsafe(32)
    if not re.fullmatch(r"[A-Za-z0-9_-]{40,60}", credential):
        raise GateError("DISPOSABLE_CREDENTIAL_GENERATION_FAILED")

    # GitHub Actions consumes this workflow command and redacts the value before
    # any database command can receive the credential. It is never an output.
    print(f"::add-mask::{credential}", flush=True)

    present = _psql(
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_catalog.pg_roles "
        f"WHERE rolname = '{role}') THEN 'present' ELSE 'absent' END;"
    )
    if present != "absent":
        raise GateError("DISPOSABLE_CANDIDATE_ROLE_ALREADY_PRESENT")

    # The generated URL-safe credential contains no SQL quoting characters.
    _psql(
        f"CREATE ROLE {role} LOGIN INHERIT PASSWORD '{credential}' "
        "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"
    )
    if _role_attributes(role) != _CANDIDATE_ATTRIBUTES:
        raise GateError("DISPOSABLE_CANDIDATE_ROLE_ATTRIBUTES_MISMATCH")
    if _role_attributes("app_runtime") != _RUNTIME_ATTRIBUTES:
        raise GateError("APP_RUNTIME_ROLE_ATTRIBUTES_MISMATCH")

    membership_count = _psql(
        "SELECT count(*) FROM pg_catalog.pg_auth_members "
        "WHERE roleid = (SELECT oid FROM pg_catalog.pg_roles "
        f"WHERE rolname = '{role}') OR member = (SELECT oid FROM pg_catalog.pg_roles "
        f"WHERE rolname = '{role}');"
    )
    if membership_count != "0":
        raise GateError("DISPOSABLE_CANDIDATE_ROLE_MEMBERSHIP_UNEXPECTED")

    _write_outputs(role, generation)
    return role, generation


def verify_contract(role: str, generation: str) -> None:
    if not _ROLE.fullmatch(role) or not _GENERATION.fullmatch(generation):
        raise GateError("DISPOSABLE_CANDIDATE_ID_INVALID")
    if _role_attributes(role) != _CANDIDATE_ATTRIBUTES:
        raise GateError("DISPOSABLE_CANDIDATE_ROLE_ATTRIBUTES_MISMATCH")
    if _role_attributes("app_runtime") != _RUNTIME_ATTRIBUTES:
        raise GateError("APP_RUNTIME_ROLE_ATTRIBUTES_MISMATCH")

    version = _psql("SELECT version_num FROM public.alembic_version;")
    if version != "20261004_0032":
        raise GateError("MIGRATION_HEAD_MISMATCH")

    registration = _psql(
        "SELECT generation || '|' || database_role || '|' || state "
        "FROM public.ai_teacher_writer_generation_state "
        "WHERE generation IN ('legacy', '" + generation + "') "
        "ORDER BY generation;"
    )
    expected = "\n".join(
        sorted(
            (
                "legacy|app_runtime|SERVING",
                f"{generation}|{role}|SERVING",
            )
        )
    )
    if registration != expected:
        raise GateError("WRITER_GENERATION_REGISTRATION_MISMATCH")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    try:
        if arguments == ["bootstrap"]:
            role, generation = bootstrap_candidate()
            print(f"GATE_MAOS_A5LR_CANDIDATE_BOOTSTRAP=PASS ROLE={role} GENERATION={generation}")
            return 0
        if len(arguments) == 3 and arguments[0] == "verify-contract":
            verify_contract(arguments[1], arguments[2])
            print("GATE_MAOS_A5LR_POST_MIGRATION_CONTRACT=PASS HEAD=20261004_0032")
            return 0
    except GateError as error:
        print("GATE_MAOS_A5LR_BLOCKED=" + str(error))
        return 1
    print("GATE_MAOS_A5LR_BLOCKED=INVALID_COMMAND")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
