"""Operator-facing primitives and database evidence for writer drain control."""

from __future__ import annotations

import re
from enum import StrEnum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class WriterState(StrEnum):
    SERVING = "SERVING"
    DRAINING = "DRAINING"
    FENCED = "FENCED"


class WriterControlError(ValueError):
    """The requested transition is not part of the fail-closed state machine."""


_GENERATION = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
_ACTIVE_WRITERS_SQL = text("""
    SELECT pg_catalog.split_part(application_name, ':', 2) AS release_generation,
           pg_catalog.split_part(application_name, ':', 3) AS instance_id,
           pg_catalog.count(*)::integer AS active_write_count
     FROM pg_catalog.pg_stat_activity
     WHERE pg_catalog.split_part(application_name, ':', 1) = 'aitw'
       AND pg_catalog.split_part(application_name, ':', 2) = :generation
       AND xact_start IS NOT NULL
       AND pid <> pg_catalog.pg_backend_pid()
     GROUP BY 1, 2
     ORDER BY 1, 2
""")
_WRITER_OBSERVATION_SQL = text("""
    WITH activity AS (
        SELECT pg_catalog.split_part(application_name, ':', 3) AS instance_id,
               pg_catalog.count(*)::integer AS active_write_count
          FROM pg_catalog.pg_stat_activity
         WHERE pg_catalog.split_part(application_name, ':', 1) = 'aitw'
           AND pg_catalog.split_part(application_name, ':', 2) = :generation
           AND xact_start IS NOT NULL
           AND pid <> pg_catalog.pg_backend_pid()
         GROUP BY 1
    )
    SELECT state.generation AS release_generation,
           activity.instance_id,
           state.state AS drain_state,
           COALESCE(activity.active_write_count, 0) AS active_write_count
      FROM public.ai_teacher_writer_generation_state AS state
      LEFT JOIN activity ON true
     WHERE state.generation = :generation
     ORDER BY activity.instance_id NULLS FIRST
""")


async def transition_writer_generation(
    session: AsyncSession, *, generation: str, target: WriterState
) -> WriterState:
    """Apply one monotonic control transition using the DB-owning operator role.

    The SELECT FOR UPDATE waits for all admitted transactions, because each
    writer retains a FOR SHARE lock until commit/rollback. app_runtime has no
    table DML rights and this helper is never exposed as an application route.
    """
    if not _GENERATION.fullmatch(generation):
        raise WriterControlError("invalid writer generation")
    if not session.in_transaction():
        raise WriterControlError("control transition requires an active transaction")
    row = (
        await session.execute(
            text("""
                SELECT state FROM public.ai_teacher_writer_generation_state
                 WHERE generation = :generation FOR UPDATE
            """),
            {"generation": generation},
        )
    ).first()
    if row is None:
        if target != WriterState.SERVING:
            raise WriterControlError("new generation must start in SERVING")
        await session.execute(
            text("""
                INSERT INTO public.ai_teacher_writer_generation_state(generation, state)
                VALUES (:generation, 'SERVING')
            """),
            {"generation": generation},
        )
        return WriterState.SERVING
    current = WriterState(row.state)
    allowed = {
        WriterState.SERVING: {WriterState.SERVING, WriterState.DRAINING},
        WriterState.DRAINING: {WriterState.DRAINING, WriterState.FENCED},
        WriterState.FENCED: {WriterState.FENCED},
    }
    if target not in allowed[current]:
        raise WriterControlError(f"illegal writer transition {current} -> {target}")
    if current != target:
        await session.execute(
            text("""
                UPDATE public.ai_teacher_writer_generation_state
                   SET state = :state, updated_at = pg_catalog.now()
                 WHERE generation = :generation
            """),
            {"generation": generation, "state": target.value},
        )
    return target


async def active_writer_transactions(session: AsyncSession, *, generation: str) -> list[dict[str, object]]:
    """Return generation/instance/count only; never expose SQL text or payloads."""
    if not _GENERATION.fullmatch(generation):
        raise WriterControlError("invalid writer generation")
    rows = (await session.execute(_ACTIVE_WRITERS_SQL, {"generation": generation})).mappings()
    return [dict(row) for row in rows]


async def writer_generation_observation(
    session: AsyncSession, *, generation: str
) -> list[dict[str, object]]:
    """Machine-checkable state/count dimensions from the DB control plane.

    Call with a monitoring identity that can observe PostgreSQL activity. The
    result contains no SQL text, payload, identity, or credential values.
    """
    if not _GENERATION.fullmatch(generation):
        raise WriterControlError("invalid writer generation")
    rows = (await session.execute(_WRITER_OBSERVATION_SQL, {"generation": generation})).mappings()
    return [dict(row) for row in rows]
