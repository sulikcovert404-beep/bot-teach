from __future__ import annotations

import pytest

from tests.ci_bootstrap_app_runtime import (
    BootstrapError,
    _verify_role,
    ensure_app_runtime_role,
    validate_database_url,
)

VALID_URL = (
    "postgresql+asyncpg://ci_migrations:ci-only@127.0.0.1:5432/"
    "ai_teacher_migrations"
)


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
    def __init__(self, *, identity=None, role=None, memberships=0):
        self.identity = identity or {
            "current_user": "ci_migrations",
            "session_user": "ci_migrations",
            "database_name": "ai_teacher_migrations",
            "server_address": "127.0.0.1",
            "actor_superuser": True,
        }
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
async def test_bootstrap_rejects_wrong_database_identity(key, value):
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
