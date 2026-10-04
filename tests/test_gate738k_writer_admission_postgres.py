"""Local-only concurrency and fencing qualification for Gate 738K.

The opt-in DSN is intentionally pinned to the disposable Docker database used
by this Gate. It must never be pointed at a shared, staging, or production DB.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.logging import writer_metrics
from app.db.base import build_session_factory
from app.services.writer_admission import (
    WriterState,
    active_writer_transactions,
    transition_writer_generation,
    writer_generation_observation,
)

EXPECTED_LOCAL_DSN = "postgresql+asyncpg://postgres@127.0.0.1:18574/ait_gate738k"
TEST_DSN = os.environ.get("GATE738K_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not TEST_DSN.startswith("postgresql+asyncpg://postgres@127.0.0.1:"),
    reason="requires an explicitly named local disposable Gate738P/Gate738K PostgreSQL",
)

_ROLE_BY_GENERATION: dict[str, str] = {}


def _new_generation(label: str) -> str:
    return f"gk{label}{uuid.uuid4().hex[:10]}"


async def _seed_generation(engine, generation: str) -> None:
    role = f"gk_{uuid.uuid4().hex[:16]}"
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE ROLE "{role}" LOGIN INHERIT NOSUPERUSER NOBYPASSRLS'))
        await connection.execute(text(f'GRANT app_runtime TO "{role}"'))
        await connection.execute(
            text("""
                INSERT INTO public.ai_teacher_writer_generation_state(generation, database_role, state)
                VALUES (:generation, :role, 'SERVING')
            """),
            {"generation": generation, "role": role},
        )
    _ROLE_BY_GENERATION[generation] = role


def _writer_factory(generation: str, instance: str):
    role = _ROLE_BY_GENERATION[generation]
    database_url = make_url(TEST_DSN).set(username=role).render_as_string(hide_password=False)
    return build_session_factory(database_url, True, generation, instance, role)


async def _create_synthetic_user(factory, label: str) -> int:
    maker = async_sessionmaker(factory.kw["bind"], expire_on_commit=False)
    async with maker() as session, session.begin():
        user_id = await session.scalar(
            text("""
                INSERT INTO public.users(username, role)
                VALUES (:username, 'STUDENT')
                RETURNING id
            """),
            {"username": label},
        )
        assert user_id is not None
        return int(user_id)


async def _set_state(engine, generation: str, state: WriterState) -> None:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        await transition_writer_generation(session, generation=generation, target=state)


async def _wait_for_db_lock(engine, application_name: str) -> bool:
    """Wait on PostgreSQL's observed lock state, rather than a blind delay."""
    async with engine.connect() as connection:
        for _ in range(100):
            waiting = await connection.scalar(
                text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_catalog.pg_stat_activity
                         WHERE application_name = :application_name
                           AND wait_event_type = 'Lock'
                    )
                """),
                {"application_name": application_name},
            )
            if waiting:
                return True
            await asyncio.sleep(0.05)
        observed = await connection.execute(text("""
            SELECT application_name, state, wait_event_type, wait_event
              FROM pg_catalog.pg_stat_activity
             WHERE application_name LIKE 'aitw:%' OR application_name LIKE 'gk-control-%'
             ORDER BY application_name
        """))
        pytest.fail(f"expected PostgreSQL lock wait for {application_name}; observed={observed.all()!r}")
    return False


@pytest.mark.asyncio
async def test_drain_waits_for_admitted_write_then_fences_restart_and_direct_sql() -> None:
    admin_engine = create_async_engine(TEST_DSN, poolclass=NullPool)
    generation = _new_generation("old")
    instance = "old1"
    await _seed_generation(admin_engine, generation)
    writer_factory = _writer_factory(generation, instance)
    old_user_id = await _create_synthetic_user(writer_factory, f"{generation}-before")
    candidate_generation = _new_generation("cand")
    await _seed_generation(admin_engine, candidate_generation)
    candidate_factory = _writer_factory(candidate_generation, "cand1")
    candidate_user_id = await _create_synthetic_user(
        candidate_factory, f"{candidate_generation}-before"
    )
    writer_maker = async_sessionmaker(writer_factory.kw["bind"], expire_on_commit=False)
    control_task: asyncio.Task[None] | None = None

    async with writer_maker() as old_session:
        await old_session.begin()
        await old_session.execute(
            text("""
                UPDATE public.users
                   SET username = :username
                 WHERE id = :user_id
            """),
            {"username": f"{generation}-committed", "user_id": old_user_id},
        )
        control_maker = async_sessionmaker(admin_engine, expire_on_commit=False)
        async with control_maker() as monitor:
            active = await active_writer_transactions(monitor, generation=generation)
        assert active == [{"release_generation": generation, "instance_id": instance, "active_write_count": 1}]
        async with control_maker() as monitor:
            observation = await writer_generation_observation(monitor, generation=generation)
        assert observation == [{
            "release_generation": generation,
            "instance_id": instance,
            "drain_state": WriterState.SERVING.value,
            "active_write_count": 1,
        }]

        async def drain() -> None:
            admin_maker = async_sessionmaker(admin_engine, expire_on_commit=False)
            async with admin_maker() as session, session.begin():
                await session.execute(
                    text("SELECT pg_catalog.set_config('application_name', :name, true)"),
                    {"name": f"gk-control-{generation}"},
                )
                await transition_writer_generation(
                    session, generation=generation, target=WriterState.DRAINING
                )

        control_task = asyncio.create_task(drain())
        assert await _wait_for_db_lock(admin_engine, f"gk-control-{generation}")

        async def queued_old_write() -> bool:
            queued_factory = _writer_factory(generation, "old2")
            queued_maker = async_sessionmaker(queued_factory.kw["bind"], expire_on_commit=False)
            async with queued_maker() as queued:
                try:
                    async with queued.begin():
                        await queued.execute(
                            text("""
                                UPDATE public.users
                                   SET username = :username
                                 WHERE id = :user_id
                            """),
                            {"username": f"{generation}-queued", "user_id": old_user_id},
                        )
                except DBAPIError:
                    return False
            return True

        queued_task = asyncio.create_task(queued_old_write())
        await asyncio.sleep(0.2)
        if queued_task.done():
            pytest.fail(f"queued writer finished before PostgreSQL lock observation: {queued_task.result()!r}")
        assert await _wait_for_db_lock(admin_engine, f"aitw:{generation}:old2")
        async with control_maker() as monitor:
            observation = await writer_generation_observation(monitor, generation=generation)
        assert sum(int(row["active_write_count"]) for row in observation) == 2
        # Candidate is a different business row and remains writable while old drain waits.
        async with candidate_factory() as candidate_session, candidate_session.begin():
            await candidate_session.execute(
                text("""
                    UPDATE public.users
                       SET username = :username
                     WHERE id = :user_id
                """),
                {"username": f"{candidate_generation}-committed", "user_id": candidate_user_id},
            )
        await old_session.commit()

    assert control_task is not None
    queued_write_committed = await queued_task
    await control_task
    async with admin_engine.connect() as connection:
        old_username = await connection.scalar(
            text("SELECT username FROM public.users WHERE id=:id"), {"id": old_user_id}
        )
        assert old_username == (
            f"{generation}-queued" if queued_write_committed else f"{generation}-committed"
        )
        assert await connection.scalar(
            text("SELECT username FROM public.users WHERE id=:id"), {"id": candidate_user_id}
        ) == f"{candidate_generation}-committed"
    assert writer_metrics.snapshot()["active_write_count"].get(f"{generation}|{instance}") == 0
    control_maker = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with control_maker() as monitor:
        observation = await writer_generation_observation(monitor, generation=generation)
    assert observation == [{
        "release_generation": generation,
        "instance_id": None,
        "drain_state": WriterState.DRAINING.value,
        "active_write_count": 0,
    }]

    async with writer_factory() as draining_writer, draining_writer.begin():
        with pytest.raises(DBAPIError, match="not serving"):
            await draining_writer.execute(
                text("UPDATE public.users SET username=:username WHERE id=:user_id"),
                {"username": f"{generation}-after-drain", "user_id": old_user_id},
            )

    await _set_state(admin_engine, generation, WriterState.FENCED)
    restarted_factory = _writer_factory(generation, "old2")
    async with restarted_factory() as restarted, restarted.begin():
        with pytest.raises(DBAPIError, match="not serving"):
            await restarted.execute(
                text("""
                    UPDATE public.ai_teacher_writer_generation_state
                       SET updated_at = pg_catalog.now()
                     WHERE generation = :generation
                """),
                {"generation": generation},
            )

    # The actual OLD login remains fenced even after a process restart and a
    # direct SQL write that bypasses the SQLAlchemy before-execute hook.
    async with admin_engine.connect() as connection:
        legacy_state = await connection.scalar(
            text("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation='legacy'")
        )
    if legacy_state == WriterState.SERVING.value:
        await _set_state(admin_engine, "legacy", WriterState.DRAINING)
    if legacy_state != WriterState.FENCED.value:
        await _set_state(admin_engine, "legacy", WriterState.FENCED)
    legacy_engine = create_async_engine(
        make_url(TEST_DSN).set(username="app_runtime").render_as_string(hide_password=False),
        poolclass=NullPool,
    )
    async with legacy_engine.begin() as connection:
        with pytest.raises(DBAPIError, match="not serving"):
            await connection.execute(text("INSERT INTO public.users DEFAULT VALUES"))
    await legacy_engine.dispose()

    async with admin_engine.connect() as connection:
        candidate_state = await connection.scalar(
            text("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation=:g"),
            {"g": candidate_generation},
        )
        old_state = await connection.scalar(
            text("SELECT state FROM public.ai_teacher_writer_generation_state WHERE generation=:g"),
            {"g": generation},
        )
    assert candidate_state == WriterState.SERVING.value
    assert old_state == WriterState.FENCED.value
    await admin_engine.dispose()


@pytest.mark.asyncio
async def test_runtime_factory_requires_postgres_and_complete_identity() -> None:
    from app.db.base import build_session_factory

    with pytest.raises(ValueError, match="requires PostgreSQL"):
        build_session_factory("sqlite+aiosqlite:///:memory:", True, "old-a", "old1")
    with pytest.raises(ValueError, match="generation and instance"):
        build_session_factory(EXPECTED_LOCAL_DSN, True, "", "")


@pytest.mark.asyncio
async def test_database_crash_rolls_back_releases_old_writer_and_keeps_fence_durable() -> None:
    admin_engine = create_async_engine(TEST_DSN, poolclass=NullPool)
    generation = _new_generation("crash")
    instance = "crashold"
    await _seed_generation(admin_engine, generation)
    writer_factory = _writer_factory(generation, instance)
    user_id = await _create_synthetic_user(writer_factory, f"{generation}-before")
    writer_maker = async_sessionmaker(writer_factory.kw["bind"], expire_on_commit=False)

    async with writer_maker() as writer:
        await writer.begin()
        await writer.execute(
            text("""
                UPDATE public.users
                   SET username = :username
                 WHERE id = :user_id
            """),
            {"username": f"{generation}-uncommitted", "user_id": user_id},
        )
        backend_pid = await writer.scalar(text("SELECT pg_catalog.pg_backend_pid()"))
        async with admin_engine.begin() as control:
            terminated = await control.scalar(
                text("SELECT pg_catalog.pg_terminate_backend(:pid)"), {"pid": backend_pid}
            )
        assert terminated is True
        with pytest.raises(DBAPIError):
            await writer.commit()

    monitor_maker = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with monitor_maker() as monitor:
        assert await active_writer_transactions(monitor, generation=generation) == []
    async with admin_engine.connect() as connection:
        assert await connection.scalar(
            text("SELECT username FROM public.users WHERE id=:id"), {"id": user_id}
        ) == f"{generation}-before"
    assert writer_metrics.snapshot()["active_write_count"].get(f"{generation}|{instance}") == 0

    await _set_state(admin_engine, generation, WriterState.DRAINING)
    await _set_state(admin_engine, generation, WriterState.FENCED)
    restarted_factory = _writer_factory(generation, "crashnew")
    async with restarted_factory() as restarted, restarted.begin():
        with pytest.raises(DBAPIError, match="not serving"):
            await restarted.execute(
                text("""
                    UPDATE public.users
                       SET username = :username
                     WHERE id = :user_id
                """),
                {"username": f"{generation}-after-fence", "user_id": user_id},
            )
    await admin_engine.dispose()
