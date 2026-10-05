"""Provision the migration's external runtime-role prerequisite in CI only."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import secrets
import subprocess
from urllib.parse import urlsplit

import asyncpg


class BootstrapError(RuntimeError):
    """A fail-closed CI role-prerequisite error without connection details."""


_SERVICE_CONTAINER_ID = re.compile(r"\A[0-9a-f]{64}\Z")
_INSPECT_NETWORKS_FORMAT = "{{json .NetworkSettings.Networks}}"


def _service_address_class(attestation_present: bool, exact_match: bool) -> str:
    if not attestation_present:
        return "ATTESTATION_UNAVAILABLE"
    if exact_match:
        return "EXACT_SERVICE_CONTAINER_MATCH"
    return "EXACT_SERVICE_CONTAINER_MISMATCH"


def _emit_service_address_attestation(
    client_target_loopback: bool, present: bool, exact_match: bool
) -> None:
    """Emit only safe attestation metadata, never a raw container address."""
    diagnostic = {
        "client_target_loopback": client_target_loopback,
        "service_address_attestation_present": present,
        "server_address_match": exact_match,
        "server_address_class": _service_address_class(present, exact_match),
    }
    print(
        "CI_SERVICE_ADDRESS_ATTESTATION "
        + json.dumps(diagnostic, separators=(",", ":"))
    )


def _attest_service_container_address(container_id: str | None):
    """Read one exact GitHub job service container address via Docker inspect."""
    if not isinstance(container_id, str) or not _SERVICE_CONTAINER_ID.fullmatch(
        container_id
    ):
        raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")
    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                _INSPECT_NETWORKS_FORMAT,
                container_id,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        networks = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, TypeError):
        raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED") from None

    if not isinstance(networks, dict) or not networks:
        raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")

    candidates = []
    for network in networks.values():
        if not isinstance(network, dict):
            raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")
        for field in ("IPAddress", "GlobalIPv6Address"):
            value = network.get(field)
            if value in (None, ""):
                continue
            if not isinstance(value, str):
                raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")
            try:
                candidates.append(ipaddress.ip_address(value))
            except ValueError:
                raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED") from None

    if len(candidates) != 1:
        raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")
    return candidates[0]


def _normalize_server_address(value):
    """Normalize only representations documented for this inet query."""
    if value is None:
        return None
    value_type = type(value)
    if value_type in (ipaddress.IPv4Address, ipaddress.IPv6Address):
        return value
    elif value_type in (ipaddress.IPv4Interface, ipaddress.IPv6Interface):
        # asyncpg decodes PostgreSQL inet as an interface when a prefix is present.
        # inet_server_addr() is a host address; reject unexpected network prefixes.
        if value.network.prefixlen != value.max_prefixlen:
            return None
        return value.ip
    elif value_type is str:
        try:
            return ipaddress.ip_address(value)
        except ValueError:
            return None
    return None


def _server_address_class(value) -> str:
    """Classify the server address without ever exposing its raw value."""
    if value is None:
        return "NULL"
    address = _normalize_server_address(value)
    if address is None:
        return "UNPARSEABLE"
    if address.version == 4 and address.is_loopback:
        return "LOOPBACK_IPV4"
    if address.version == 6 and address.is_loopback:
        return "LOOPBACK_IPV6"
    return "NON_LOOPBACK"


def _server_address_matches(value, attested_address) -> bool:
    """Require exact equality with the single attested service-container IP."""
    actual = _normalize_server_address(value)
    return (
        type(attested_address) in (ipaddress.IPv4Address, ipaddress.IPv6Address)
        and actual is not None
        and actual == attested_address
    )


def _emit_identity_diagnostic(
    identity, attested_address, client_target_loopback: bool
) -> None:
    """Emit deterministic predicate evidence, never identity values or a DSN."""
    row_present = identity is not None
    current_user_match = row_present and identity["current_user"] == "ci_migrations"
    session_user_match = row_present and identity["session_user"] == "ci_migrations"
    database_match = row_present and identity["database_name"] == "ai_teacher_migrations"
    address = identity["server_address"] if row_present else None
    address_match = row_present and _server_address_matches(address, attested_address)
    attestation_present = type(attested_address) in (
        ipaddress.IPv4Address,
        ipaddress.IPv6Address,
    )
    actor_superuser = row_present and bool(identity["actor_superuser"])
    diagnostic = {
        "identity_row_present": row_present,
        "current_user_match": current_user_match,
        "session_user_match": session_user_match,
        "database_match": database_match,
        "client_target_loopback": client_target_loopback,
        "server_address_match": address_match,
        "service_address_attestation_present": attestation_present,
        "server_address_class": _service_address_class(
            attestation_present, address_match
        ),
        "actor_superuser": actor_superuser,
        "current_equals_session": (
            row_present and identity["current_user"] == identity["session_user"]
        ),
    }
    print("CI_DB_IDENTITY_DIAGNOSTIC " + json.dumps(diagnostic, separators=(",", ":")))


def validate_database_url(value: str) -> bool:
    """Restrict this helper to the dedicated local CI PostgreSQL service."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or parsed.port != 5432
        or parsed.username != "ci_migrations"
        or not parsed.password
        or parsed.path != "/ai_teacher_migrations"
        or parsed.query
        or parsed.fragment
    ):
        raise BootstrapError("DATABASE_TARGET_NOT_DEDICATED_CI_POSTGRES")
    return True


def _verify_role(role) -> None:
    expected = {
        "rolcanlogin": True,
        "rolinherit": True,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }
    if role is None or any(role[key] is not value for key, value in expected.items()):
        raise BootstrapError("APP_RUNTIME_ROLE_ATTRIBUTES_MISMATCH")


async def ensure_app_runtime_role(
    connection,
    *,
    attested_address,
    client_target_loopback: bool,
    password_factory=secrets.token_urlsafe,
) -> None:
    """Create the role only when absent; never mutate a pre-existing role."""
    if client_target_loopback is not True:
        _emit_service_address_attestation(False, False, False)
        raise BootstrapError("DATABASE_TARGET_NOT_DEDICATED_CI_POSTGRES")
    if type(attested_address) not in (ipaddress.IPv4Address, ipaddress.IPv6Address):
        _emit_service_address_attestation(client_target_loopback, False, False)
        raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")
    identity = await connection.fetchrow("""
        SELECT current_user AS current_user, session_user AS session_user,
               current_database() AS database_name,
               inet_server_addr() AS server_address,
               actor.rolsuper AS actor_superuser
          FROM pg_catalog.pg_roles AS actor
         WHERE actor.rolname = current_user
    """)
    if (
        identity is None
        or identity["current_user"] != "ci_migrations"
        or identity["session_user"] != "ci_migrations"
        or identity["database_name"] != "ai_teacher_migrations"
        or not _server_address_matches(identity["server_address"], attested_address)
        or not identity["actor_superuser"]
    ):
        _emit_identity_diagnostic(identity, attested_address, client_target_loopback)
        raise BootstrapError("DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES")

    _emit_identity_diagnostic(identity, attested_address, client_target_loopback)

    role = await connection.fetchrow("""
        SELECT rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
               rolreplication, rolbypassrls
          FROM pg_catalog.pg_roles
         WHERE rolname = 'app_runtime'
    """)
    if role is None:
        password = password_factory(32)
        statement = await connection.fetchval(
            """SELECT format(
                'CREATE ROLE app_runtime LOGIN INHERIT NOSUPERUSER '
                'NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
                CAST($1 AS text)
            )""",
            password,
        )
        await connection.execute(statement)
        role = await connection.fetchrow("""
            SELECT rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
                   rolreplication, rolbypassrls
              FROM pg_catalog.pg_roles
             WHERE rolname = 'app_runtime'
        """)
    _verify_role(role)

    membership_count = await connection.fetchval("""
        SELECT count(*)
          FROM pg_catalog.pg_auth_members AS membership
          JOIN pg_catalog.pg_roles AS member ON member.oid = membership.member
         WHERE member.rolname = 'app_runtime'
    """)
    if membership_count != 0:
        raise BootstrapError("APP_RUNTIME_ROLE_MEMBERSHIP_NOT_EMPTY")


async def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    try:
        client_target_loopback = validate_database_url(database_url)
        if os.environ.get("GITHUB_ACTIONS") != "true":
            _emit_service_address_attestation(client_target_loopback, False, False)
            raise BootstrapError("CI_SERVICE_ADDRESS_ATTESTATION_FAILED")
        try:
            attested_address = _attest_service_container_address(
                os.environ.get("CI_POSTGRES_SERVICE_ID")
            )
        except BootstrapError:
            _emit_service_address_attestation(client_target_loopback, False, False)
            raise
        connection = await asyncpg.connect(
            database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            await ensure_app_runtime_role(
                connection,
                attested_address=attested_address,
                client_target_loopback=client_target_loopback,
            )
        finally:
            await connection.close()
    except BootstrapError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 -- redact connection/driver details.
        raise SystemExit(f"CI_ROLE_BOOTSTRAP_FAILED ({type(exc).__name__})") from None
    print("Verified app_runtime prerequisite in disposable CI PostgreSQL.")


if __name__ == "__main__":
    asyncio.run(main())
