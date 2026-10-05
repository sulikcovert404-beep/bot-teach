"""Provision the migration's external runtime-role prerequisite in CI only."""
from __future__ import annotations

import asyncio
import os
import secrets
from urllib.parse import urlsplit

import asyncpg


class BootstrapError(RuntimeError):
    """A fail-closed CI role-prerequisite error without connection details."""


def validate_database_url(value: str) -> None:
    """Restrict this helper to the dedicated local CI PostgreSQL service."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.port != 5432
        or parsed.username != "ci_migrations"
        or not parsed.password
        or parsed.path != "/ai_teacher_migrations"
        or parsed.query
        or parsed.fragment
    ):
        raise BootstrapError("DATABASE_TARGET_NOT_DEDICATED_CI_POSTGRES")


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


async def ensure_app_runtime_role(connection, password_factory=secrets.token_urlsafe) -> None:
    """Create the role only when absent; never mutate a pre-existing role."""
    identity = await connection.fetchrow("""
        SELECT current_user AS current_user, session_user AS session_user,
               current_database() AS database_name,
               inet_server_addr()::text AS server_address,
               actor.rolsuper AS actor_superuser
          FROM pg_catalog.pg_roles AS actor
         WHERE actor.rolname = current_user
    """)
    if (
        identity is None
        or identity["current_user"] != "ci_migrations"
        or identity["session_user"] != "ci_migrations"
        or identity["database_name"] != "ai_teacher_migrations"
        or identity["server_address"] not in {"127.0.0.1", "::1"}
        or not identity["actor_superuser"]
    ):
        raise BootstrapError("DATABASE_IDENTITY_NOT_DEDICATED_CI_POSTGRES")

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
                $1
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
        validate_database_url(database_url)
        connection = await asyncpg.connect(
            database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            await ensure_app_runtime_role(connection)
        finally:
            await connection.close()
    except BootstrapError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 -- redact connection/driver details.
        raise SystemExit(f"CI_ROLE_BOOTSTRAP_FAILED ({type(exc).__name__})") from None
    print("Verified app_runtime prerequisite in disposable CI PostgreSQL.")


if __name__ == "__main__":
    asyncio.run(main())
