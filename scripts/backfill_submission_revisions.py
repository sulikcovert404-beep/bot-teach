"""Resumable, bounded backfill for the Gate738E candidate schema.

This utility is intentionally restricted to loopback PostgreSQL databases with
an explicit Gate738E disposable database name. It never prints the connection
URL or credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from urllib.parse import urlparse

import asyncpg

EXPECTED_EXPAND_REVISIONS = {"20261003_0028", "20261003_0029"}


def _safe_dsn() -> str:
    if os.environ.get("GATE738E_DISPOSABLE") != "1":
        raise SystemExit("Set GATE738E_DISPOSABLE=1 only for the isolated disposable rehearsal")
    raw = os.environ.get("DATABASE_URL", "")
    parsed = urlparse(raw.replace("postgresql+asyncpg://", "postgresql://", 1))
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise SystemExit("DATABASE_URL must identify the Gate738E disposable PostgreSQL database")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Gate738E backfill is loopback-only")
    if not (parsed.path.lstrip("/").startswith("gate738e_")):
        raise SystemExit("Gate738E backfill requires a gate738e_* disposable database name")
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _scalar(conn: asyncpg.Connection, query: str) -> int:
    return int(await conn.fetchval(query) or 0)


async def _validate(conn: asyncpg.Connection) -> dict[str, int]:
    errors = {
        "missing_current_revision": await _scalar(conn, """
            SELECT count(*) FROM public.student_submissions s
             WHERE s.status IN ('SUBMITTED', 'REVIEWED')
               AND NOT EXISTS (
                   SELECT 1 FROM public.submission_revisions r
                    WHERE r.id = s.current_revision_id
                      AND r.submission_id = s.id AND r.tenant_id = s.tenant_id
                      AND r.revision_no = s.revision
               )
        """),
        "pointer_on_unsubmitted": await _scalar(conn, """
            SELECT count(*) FROM public.student_submissions
             WHERE status = 'NOT_SUBMITTED' AND current_revision_id IS NOT NULL
        """),
        "unsubmitted_with_content": await _scalar(conn, """
            SELECT count(*) FROM public.student_submissions
             WHERE status = 'NOT_SUBMITTED' AND content_json IS NOT NULL
        """),
        "unlinked_reviews": await _scalar(conn, """
            SELECT count(*) FROM public.submission_reviews r
             WHERE r.submission_revision_id IS NULL
                OR NOT EXISTS (
                    SELECT 1 FROM public.submission_revisions sr
                     WHERE sr.id = r.submission_revision_id
                       AND sr.submission_id = r.submission_id
                       AND sr.tenant_id = r.tenant_id
                )
        """),
        "review_on_unsubmitted": await _scalar(conn, """
            SELECT count(*) FROM public.submission_reviews r
              JOIN public.student_submissions s ON s.id = r.submission_id
             WHERE s.status = 'NOT_SUBMITTED'
        """),
        "orphan_revisions": await _scalar(conn, """
            SELECT count(*) FROM public.submission_revisions r
             WHERE NOT EXISTS (
                 SELECT 1 FROM public.student_submissions s
                  WHERE s.id = r.submission_id AND s.tenant_id = r.tenant_id
             )
        """),
        "legacy_identity_mismatch": await _scalar(conn, """
            SELECT count(*) FROM public.student_submissions s
              JOIN public.submission_revisions r ON r.id = s.current_revision_id
             WHERE r.submission_id <> s.id OR r.tenant_id <> s.tenant_id
        """),
    }
    return errors


async def run(batch_size: int, idle_timeout: float, max_batches: int | None = None) -> None:
    dsn = _safe_dsn()
    conn = await asyncpg.connect(dsn)
    started = time.monotonic()
    try:
        current = await conn.fetchval("SELECT version_num FROM public.alembic_version")
        if current not in EXPECTED_EXPAND_REVISIONS:
            raise SystemExit(f"Expected Gate738E expanded revision; observed {current!r}")
        bypass = await conn.fetchval("""
            SELECT rolsuper OR rolbypassrls
              FROM pg_catalog.pg_roles
             WHERE rolname = current_user
        """)
        if not bypass:
            raise SystemExit("Gate738E backfill requires the isolated migration identity to bypass RLS")
        state = await conn.fetchval(
            "SELECT status FROM public.submission_revision_backfill_state WHERE singleton = true"
        )
        if state not in {"PENDING", "RUNNING", "VALIDATED"}:
            raise SystemExit(f"Backfill state is not resumable: {state!r}")

        if state != "VALIDATED":
            completed_batches = 0
            await conn.execute("""
                UPDATE public.submission_revision_backfill_state
                   SET status='RUNNING', updated_at=pg_catalog.now()
                 WHERE singleton=true
            """)

            while True:
                async with conn.transaction():
                    parents = await conn.fetch("""
                        SELECT s.id
                          FROM public.student_submissions s
                         WHERE s.status IN ('SUBMITTED', 'REVIEWED')
                           AND (
                               s.current_revision_id IS NULL
                               OR EXISTS (
                                   SELECT 1 FROM public.submission_reviews r
                                    WHERE r.submission_id=s.id
                                      AND r.submission_revision_id IS NULL
                               )
                           )
                         ORDER BY s.id
                         LIMIT $1
                         FOR UPDATE OF s SKIP LOCKED
                    """, batch_size)

                    for selected in parents:
                        parent = await conn.fetchrow("""
                            SELECT id, tenant_id, revision, content_json, submitted_at,
                                   status, current_revision_id
                              FROM public.student_submissions
                             WHERE id=$1
                             FOR UPDATE
                        """, selected["id"])
                        if parent is None:
                            continue
                        child = await conn.fetchrow("""
                            SELECT id, tenant_id, content_json
                              FROM public.submission_revisions
                             WHERE submission_id=$1 AND revision_no=$2
                        """, parent["id"], parent["revision"])
                        if child is None:
                            child_id = await conn.fetchval("""
                                INSERT INTO public.submission_revisions
                                    (submission_id, tenant_id, revision_no, content_json,
                                     submitted_at, provenance)
                                VALUES ($1, $2, $3, $4, $5, 'BASELINE_BACKFILL')
                                ON CONFLICT (submission_id, revision_no) DO NOTHING
                                RETURNING id
                            """, parent["id"], parent["tenant_id"], parent["revision"],
                                parent["content_json"], parent["submitted_at"])
                            if child_id is None:
                                child = await conn.fetchrow("""
                                    SELECT id, tenant_id, content_json
                                      FROM public.submission_revisions
                                     WHERE submission_id=$1 AND revision_no=$2
                                """, parent["id"], parent["revision"])
                                child_id = child["id"] if child else None
                            if child_id is None:
                                raise RuntimeError("Backfill could not resolve an idempotent revision insert")
                        else:
                            child_id = child["id"]
                            if child["tenant_id"] != parent["tenant_id"]:
                                raise RuntimeError("Existing revision tenant does not match its parent")
                            if child["content_json"] != parent["content_json"]:
                                raise RuntimeError("Existing revision content conflicts with the parent snapshot")

                        await conn.execute("""
                            UPDATE public.student_submissions
                               SET current_revision_id=$2
                             WHERE id=$1 AND current_revision_id IS DISTINCT FROM $2
                        """, parent["id"], child_id)
                        review_count = await conn.fetchval("""
                            SELECT count(*) FROM public.submission_reviews
                             WHERE submission_id=$1 AND submission_revision_id IS NULL
                        """, parent["id"])
                        await conn.execute("""
                            UPDATE public.submission_reviews
                               SET submission_revision_id=$2,
                                   association_provenance='MIGRATION_BASELINE_ONLY'
                             WHERE submission_id=$1 AND submission_revision_id IS NULL
                        """, parent["id"], child_id)
                        await conn.execute("""
                            UPDATE public.submission_revision_backfill_state
                               SET last_submission_id=GREATEST(COALESCE(last_submission_id, 0), $1),
                                   processed_submissions=processed_submissions+1,
                                   processed_reviews=processed_reviews+$2,
                                   updated_at=pg_catalog.now()
                             WHERE singleton=true
                        """, parent["id"], review_count)

                if not parents:
                    errors = await _validate(conn)
                    if not any(errors.values()):
                        break
                    if time.monotonic() - started >= idle_timeout:
                        raise RuntimeError(f"DO NOT CONTRACT; backfill has unresolved rows: {errors}")
                    await asyncio.sleep(0.1)
                else:
                    completed_batches += 1
                    if max_batches is not None and completed_batches >= max_batches:
                        raise RuntimeError(
                            "BACKFILL_PAUSED after a committed bounded batch; rerun to resume"
                        )

        errors = await _validate(conn)
        if any(errors.values()):
            raise RuntimeError(f"Gate738E validation failed; DO NOT CONTRACT: {errors}")
        summary = await conn.fetchrow("""
            SELECT
                (SELECT count(*) FROM public.student_submissions) AS submissions,
                (SELECT count(*) FROM public.submission_revisions) AS revisions,
                (SELECT count(*) FROM public.submission_reviews) AS reviews
        """)
        await conn.execute("""
            UPDATE public.submission_revision_backfill_state
               SET status='VALIDATED', validated_at=pg_catalog.now(), updated_at=pg_catalog.now()
             WHERE singleton=true
        """)
        print(
            "Gate738E backfill validated: "
            f"submissions={summary['submissions']} revisions={summary['revisions']} "
            f"reviews={summary['reviews']} errors=0"
        )
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--idle-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-batches", type=int)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 10_000:
        parser.error("--batch-size must be between 1 and 10000")
    if not 1 <= args.idle_timeout_seconds <= 600:
        parser.error("--idle-timeout-seconds must be between 1 and 600")
    if args.max_batches is not None and args.max_batches < 1:
        parser.error("--max-batches must be positive")
    asyncio.run(run(args.batch_size, args.idle_timeout_seconds, args.max_batches))


if __name__ == "__main__":
    main()
