"""Disposable PostgreSQL qualification for the frozen A12F adapter."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import User
from app.security.authority_snapshot import (
    A11LifecycleStateReader,
    PrincipalLifecycleState,
    resolve_principal_authority_snapshot,
)
from app.security.tokens import create_access_token, decode_access_token_claims

TEST_DSN = os.environ.get("MAOS_A12FQ_TEST_DSN", "").strip()
pytestmark = pytest.mark.asyncio


async def test_frozen_snapshot_uses_real_a11_postgres_resolver() -> None:
    if not TEST_DSN:
        pytest.skip("MAOS_A12FQ_TEST_DSN must point to a fresh disposable PostgreSQL 16 database")

    engine = create_async_engine(TEST_DSN)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_ids: dict[str, int] = {}
    lifecycle_queries: list[str] = []

    def record_lifecycle_query(connection, cursor, statement, parameters, context, executemany):
        del connection, cursor, parameters, context, executemany
        if statement.lstrip().lower().startswith("select maos_lifecycle.resolve_state("):
            lifecycle_queries.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record_lifecycle_query)
    try:
        async with engine.connect() as connection:
            facts = (
                await connection.execute(
                    text(
                        """SELECT current_setting('server_version_num')::integer AS version,
                                  (SELECT version_num FROM public.alembic_version) AS revision,
                                  pg_catalog.has_function_privilege(
                                    'maos_lifecycle_writer',
                                    'maos_lifecycle.resolve_state(text)', 'EXECUTE'
                                  ) AS writer_resolve,
                                  pg_catalog.has_function_privilege(
                                    'app_runtime',
                                    'maos_lifecycle.resolve_state(text)', 'EXECUTE'
                                  ) AS runtime_resolve,
                                  (SELECT rolcanlogin FROM pg_catalog.pg_roles
                                   WHERE rolname='maos_lifecycle_writer') AS writer_login,
                                  pg_catalog.pg_has_role(
                                    'app_runtime','maos_lifecycle_writer','MEMBER'
                                  ) AS runtime_writer"""
                    )
                )
            ).mappings().one()
        assert facts["version"] // 10000 == 16
        assert facts["revision"] == "20261006_0035"
        assert facts["writer_resolve"] is True
        assert facts["runtime_resolve"] is False
        assert facts["writer_login"] is False
        assert facts["runtime_writer"] is False

        async with sessions() as user_session:
            seeded_user_ids = list(
                await user_session.scalars(
                    select(User.id).where(User.role == "TEACHER").order_by(User.id).limit(4)
                )
            )
            assert len(seeded_user_ids) == 4, (
                "fresh PostgreSQL fixture must contain four TEACHER rows seeded before "
                "the writer-admission fence"
            )
            user_ids = dict(
                zip(
                    ("UNRECONCILED", "ACTIVE", "SUSPENDED", "DISABLED"),
                    seeded_user_ids,
                    strict=True,
                )
            )

            expected = {
                "UNRECONCILED": PrincipalLifecycleState.UNRECONCILED,
                "ACTIVE": PrincipalLifecycleState.ACTIVE,
                "SUSPENDED": PrincipalLifecycleState.SUSPENDED,
                "DISABLED": PrincipalLifecycleState.DISABLED,
            }
            async with sessions() as seed_session, seed_session.begin():
                await seed_session.execute(text("SET LOCAL ROLE maos_lifecycle_writer"))
                for state, expected_state in expected.items():
                    principal_ref = f"user:{user_ids[state]}"
                    current_state = await seed_session.scalar(
                        text("SELECT maos_lifecycle.resolve_state(:principal_ref)"),
                        {"principal_ref": principal_ref},
                    )
                    if state == "UNRECONCILED" or current_state == expected_state.value:
                        assert current_state == expected_state.value
                        continue
                    assert current_state == "UNRECONCILED"
                    await seed_session.execute(
                        text(
                            """SELECT maos_lifecycle.append_event(
                                       :event_id, :principal_ref, 'actor:a12fq',
                                       'UNRECONCILED', :target_state, 'reason:a12fq',
                                       'authority:a12fq', :digest, :audit_ref, :occurred_at
                                   )"""
                        ),
                        {
                            "event_id": uuid4(),
                            "principal_ref": principal_ref,
                            "target_state": state,
                            "digest": "a" * 64,
                            "audit_ref": f"audit:{state.lower()}",
                            "occurred_at": datetime.now(UTC),
                        },
                    )

            secret = "a12fq-test-secret-value-long-enough-for-hmac-sha256"
            adapter_lifecycle_queries: list[str] = []
            for state, user_id in user_ids.items():
                async with sessions() as lifecycle_session, lifecycle_session.begin():
                    await lifecycle_session.execute(
                        text("SET LOCAL ROLE maos_lifecycle_writer")
                    )
                    token = create_access_token(
                        str(user_id), secret, role="SUPER_ADMIN"
                    )
                    claims = decode_access_token_claims(token, secret)
                    query_count_before = len(lifecycle_queries)
                    snapshot = await resolve_principal_authority_snapshot(
                        claims["sub"],
                        user_session,
                        A11LifecycleStateReader(lifecycle_session),
                    )
                    adapter_lifecycle_queries.extend(
                        lifecycle_queries[query_count_before:]
                    )
                    assert snapshot.principal_id == user_id
                    assert snapshot.role == "TEACHER"
                    assert snapshot.lifecycle_state is expected[state]

            async with sessions() as runtime_session, runtime_session.begin():
                await runtime_session.execute(text("SET LOCAL ROLE app_runtime"))
                query_count_before = len(lifecycle_queries)
                with pytest.raises(DBAPIError):
                    await runtime_session.scalar(
                        text("SELECT maos_lifecycle.resolve_state('user:1')")
                    )
                denied_query_count = len(lifecycle_queries) - query_count_before
            assert len(adapter_lifecycle_queries) == 4
            assert denied_query_count == 1
            assert all(
                query.lstrip().upper().startswith("SELECT")
                for query in adapter_lifecycle_queries
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record_lifecycle_query)
        await engine.dispose()
