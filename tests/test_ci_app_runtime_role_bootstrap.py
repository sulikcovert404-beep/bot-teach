from __future__ import annotations

import ipaddress
import json

import pytest

from tests.ci_bootstrap_app_runtime import (
    BootstrapError,
    _server_address_class,
    _verify_role,
    ensure_app_runtime_role,
    validate_database_url,
)

VALID_URL = (
    "postgresql+asyncpg://ci_migrations:ci-only@127.0.0.1:5432/"
    "ai_teacher_migrations"
)
DEFAULT_IDENTITY = object()


@pytest.mark.parametrize(
    "value",
    [
        VALID_URL.replace("postgresql+asyncpg", "postgresql"),
        VALID_URL.replace("127.0.0.1", "shared-db"),
        VALID_URL.replace(":5432", ":5433"),
        VALID_URL.replace("ci_migrations", "postgres"),
        VALID_URL.replace("ai_teacher_migrations", "production"),
        VALID_URL.replace("ci-only@", "@"),
        VALID_URL + "?sslmode=require",
        VALID_URL + "#external",
    ],
)
def test_database_target_rejects_non_dedicated_ci_urls(value):
    with pytest.raises(BootstrapError, match="DATABASE_TARGET_NOT_DEDICATED_CI_POSTGRES"):
        validate_database_url(value)


def test_database_target_accepts_dedicated_loopback_ci_url():
    validate_database_url(VALID_URL)


class FakeConnection:
    def __init__(self, *, identity=DEFAULT_IDENTITY, role=None, memberships=0):
        self.identity = {
            "current_user": "ci_migrations",
            "session_user": "ci_migrations",
            "database_name": "ai_teacher_migrations",
            "server_address": "127.0.0.1",
            "actor_superuser": True,
        } if identity is DEFAULT_IDENTITY else identity
        self.role = role
        self.memberships = memberships
        self.executed = []
        self.created_role = False

    async def fetchrow(self, query):
        if "current_user AS current_user" in query:
            return self.identity
        if self.role is None and self.created_role:
            return {
                "rolcanlogin": True,
                "rolinherit": True,
                "rolsuper": False,
                "rolcreatedb": False,
                "rolcreaterole": False,
                "rolreplication": False,
                "rolbypassrls": False,
            }
        return self.role

    async def fetchval(self, query, *args):
        if "format('CREATE ROLE app_runtime" in query:
            assert len(args) == 1 and args[0] == "ephemeral-only"
            return "CREATE ROLE app_runtime [password redacted]"
        return self.memberships

    async def execute(self, statement):
        self.executed.append("CREATE ROLE app_runtime")
        self.created_role = True


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("current_user", "postgres"),
        ("session_user", "postgres"),
        ("database_name", "other_database"),
        ("server_address", "203.0.113.7"),
        ("actor_superuser", False),
    ],
)
@pytest.mark.asyncio
async def test_bootstrap_rejects_wrong_database_identity(key, value, capsys):
    identity = {
        "current_user": "ci_migrations",
        "session_user": "ci_migrations",
        "database_name": "ai_teacher_migrations",
        "server_address": "127.0.0.1",
        "actor_superuser": True,
    }
    identity[key] = value
    connection = FakeConnection(identity=identity)

    with pytest.raises(BootstrapError, match="DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES"):
        await ensure_app_runtime_role(connection, lambda _: "ephemeral-only")
    diagnostic = json.loads(
        capsys.readouterr().out.strip().removeprefix("CI_DB_IDENTITY_DIAGNOSTIC ")
    )
    if key == "actor_superuser":
        assert diagnostic["actor_superuser"] is False
    elif key == "server_address":
        assert diagnostic["server_address_class"] == "NON_LOOPBACK"
        assert diagnostic["server_address_match"] is False
    assert connection.executed == []


@pytest.mark.parametrize(
    ("key", "value", "diagnostic_key", "diagnostic_value"),
    [
        ("current_user", "unexpected_actor", "current_user_match", False),
        ("session_user", "unexpected_session", "session_user_match", False),
        ("database_name", "unexpected_database", "database_match", False),
    ],
)
@pytest.mark.asyncio
async def test_identity_failure_emits_only_the_failing_actor_or_database_predicate(
    key, value, diagnostic_key, diagnostic_value, capsys
):
    identity = {
        "current_user": "ci_migrations",
        "session_user": "ci_migrations",
        "database_name": "ai_teacher_migrations",
        "server_address": "127.0.0.1",
        "actor_superuser": True,
    }
    identity[key] = value
    connection = FakeConnection(identity=identity)

    with pytest.raises(BootstrapError, match="DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES"):
        await ensure_app_runtime_role(connection, lambda _: "diagnostic-secret")

    line = capsys.readouterr().out.strip()
    assert line.startswith("CI_DB_IDENTITY_DIAGNOSTIC ")
    data = json.loads(line.removeprefix("CI_DB_IDENTITY_DIAGNOSTIC "))
    assert data[diagnostic_key] is diagnostic_value
    assert sum(
        data[key] is False
        for key in ("current_user_match", "session_user_match", "database_match")
    ) == 1
    assert value not in line
    assert connection.executed == []


def test_server_address_classification_distinguishes_loopback_families():
    assert _server_address_class("127.0.0.1") == "LOOPBACK_IPV4"
    assert _server_address_class("::1") == "LOOPBACK_IPV6"
    assert _server_address_class("203.0.113.7") == "NON_LOOPBACK"
    assert _server_address_class(None) == "NULL"


@pytest.mark.parametrize(
    ("address", "expected_class", "expected_match"),
    [
        ("203.0.113.7", "NON_LOOPBACK", False),
        (ipaddress.IPv4Address("172.17.0.2"), "NON_LOOPBACK", False),
        (ipaddress.IPv4Address("10.0.0.2"), "NON_LOOPBACK", False),
        (ipaddress.IPv6Address("2001:db8::1"), "NON_LOOPBACK", False),
        (None, "NULL", False),
        ("127.0.0.1", "LOOPBACK_IPV4", True),
        ("::1", "LOOPBACK_IPV6", True),
        (ipaddress.IPv4Address("127.0.0.1"), "LOOPBACK_IPV4", True),
        (ipaddress.IPv6Address("::1"), "LOOPBACK_IPV6", True),
        (ipaddress.IPv4Interface("127.0.0.1/32"), "LOOPBACK_IPV4", True),
        (ipaddress.IPv6Interface("::1/128"), "LOOPBACK_IPV6", True),
        (ipaddress.IPv4Address("127.0.0.2"), "LOOPBACK_IPV4", False),
        (ipaddress.IPv4Interface("127.0.0.1/24"), "UNPARSEABLE", False),
        ("localhost", "UNPARSEABLE", False),
        ("not-an-ip", "UNPARSEABLE", False),
        ("not-an-address", "UNPARSEABLE", False),
        (b"127.0.0.1", "UNPARSEABLE", False),
        (object(), "UNPARSEABLE", False),
    ],
)
@pytest.mark.asyncio
async def test_server_address_diagnostic_is_classified_and_redacted(
    address, expected_class, expected_match, capsys
):
    identity = {
        "current_user": "ci_migrations",
        "session_user": "ci_migrations",
        "database_name": "ai_teacher_migrations",
        "server_address": address,
        "actor_superuser": True,
    }
    connection = FakeConnection(identity=identity)

    if expected_match:
        await ensure_app_runtime_role(connection, lambda _: "diagnostic-secret")
        output = capsys.readouterr().out
        assert output == ""
        assert len(connection.executed) == 1
        return

    with pytest.raises(BootstrapError, match="DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES"):
        await ensure_app_runtime_role(connection, lambda _: "diagnostic-secret")

    output = capsys.readouterr().out.strip()
    line = output.removeprefix("CI_DB_IDENTITY_DIAGNOSTIC ")
    data = json.loads(line)
    assert data["server_address_class"] == expected_class
    assert data["server_address_match"] is False
    assert "203.0.113.7" not in output
    assert "diagnostic-secret" not in output
    assert "postgresql" not in output
    assert connection.executed == []


@pytest.mark.asyncio
async def test_absent_identity_row_is_diagnosed_and_fails_before_role_creation(capsys):
    connection = FakeConnection(identity=None)

    with pytest.raises(BootstrapError, match="DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES"):
        await ensure_app_runtime_role(connection)

    data = json.loads(
        capsys.readouterr().out.strip().removeprefix("CI_DB_IDENTITY_DIAGNOSTIC ")
    )
    assert data["identity_row_present"] is False
    assert data["server_address_class"] == "NULL"
    assert connection.executed == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("rolcanlogin", False),
        ("rolinherit", False),
        ("rolsuper", True),
        ("rolcreatedb", True),
        ("rolcreaterole", True),
        ("rolreplication", True),
        ("rolbypassrls", True),
    ],
)
def test_role_contract_rejects_privilege_or_login_mismatch(key, value):
    role = {
        "rolcanlogin": True,
        "rolinherit": True,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }
    role[key] = value
    with pytest.raises(BootstrapError, match="APP_RUNTIME_ROLE_ATTRIBUTES_MISMATCH"):
        _verify_role(role)


@pytest.mark.asyncio
async def test_existing_role_is_verified_without_mutation():
    role = {
        "rolcanlogin": True,
        "rolinherit": True,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }
    connection = FakeConnection(role=role)
    await ensure_app_runtime_role(connection)
    assert connection.executed == []


@pytest.mark.asyncio
async def test_role_with_membership_fails_closed_without_role_mutation():
    role = {
        "rolcanlogin": True,
        "rolinherit": True,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }
    connection = FakeConnection(role=role, memberships=1)
    with pytest.raises(BootstrapError, match="APP_RUNTIME_ROLE_MEMBERSHIP_NOT_EMPTY"):
        await ensure_app_runtime_role(connection)
    assert connection.executed == []


@pytest.mark.asyncio
async def test_absent_role_is_created_with_ephemeral_credential_then_verified():
    connection = FakeConnection()
    await ensure_app_runtime_role(connection, lambda _: "ephemeral-only")
    assert len(connection.executed) == 1
    assert "CREATE ROLE app_runtime" in connection.executed[0]
    assert "ALTER ROLE" not in connection.executed[0]
    assert "ephemeral-only" not in connection.executed[0]
