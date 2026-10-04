"""Resume/replay the frozen backfill around concurrent legacy writes.

This probe only changes one uniquely named database on a loopback disposable
PostgreSQL cluster. It never modifies application or migration source files.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DSN = os.environ["GATE738H_ADMIN_DSN"]
assert os.environ.get("GATE738H_DISPOSABLE") == "1"
parsed = urlparse(ADMIN_DSN)
assert parsed.scheme in {"postgres", "postgresql"}
assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
assert parsed.path.lstrip("/") == "postgres"


def dsn(database: str, *, sqlalchemy: bool = False) -> str:
    value = urlunparse(parsed._replace(path=f"/{database}"))
    return value.replace("postgresql://", "postgresql+asyncpg://", 1) if sqlalchemy else value


def command(args: list[str], database: str, *, expect_pause: bool = False) -> str:
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
    env["GATE738E_DISPOSABLE"] = "1"
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True,
                            timeout=240, check=False)
    combined = result.stdout + result.stderr
    if expect_pause:
        assert result.returncode != 0 and "BACKFILL_PAUSED" in combined, combined[-2000:]
    elif result.returncode:
        raise RuntimeError(combined[-2500:])
    return combined


async def main() -> None:
    # Reuse the already-qualified synthetic seed and DSN helpers without
    # invoking that module's test runner.
    import runpy
    helpers = runpy.run_path(os.path.join(ROOT, "tests", "gate738h_qualification.py"))
    admin = await asyncpg.connect(ADMIN_DSN)
    database = "gate738e_gate738h_recovery_" + uuid4().hex
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
    finally:
        await admin.close()
    try:
        command([sys.executable, "-B", "-m", "alembic", "upgrade", "20260921_0022"], database)
        _teacher, _assignment, _last_profile = await helpers["seed"](database, 200)
        for revision in ("20261003_0027", "20261003_0028", "20261003_0029"):
            command([sys.executable, "-B", "-m", "alembic", "upgrade", revision], database)

        # Intentional process exit after one committed bounded batch represents
        # an interruption, with durable cursor/state evidence checked below.
        command([sys.executable, "-B", "scripts/backfill_submission_revisions.py",
                 "--batch-size", "25", "--idle-timeout-seconds", "10", "--max-batches", "1"],
                database, expect_pause=True)
        connection = await asyncpg.connect(dsn(database))
        try:
            state = await connection.fetchrow(
                "SELECT status,processed_submissions FROM submission_revision_backfill_state WHERE singleton=true"
            )
            assert state["status"] == "RUNNING" and state["processed_submissions"] == 25, dict(state)
            target = await connection.fetchrow(
                "SELECT id FROM student_submissions ORDER BY id DESC LIMIT 1"
            )
            target_id = target["id"]
            await connection.execute("""
                UPDATE student_submissions
                   SET status='REVIEWED',revision=2,content_json='legacy-during-pause',submitted_at=now()
                 WHERE id=$1
            """, target_id)
            teacher = await connection.fetchval("SELECT id FROM users WHERE role='TEACHER' ORDER BY id LIMIT 1")
            await connection.execute("""
                INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
                VALUES($1,'gate738h', 'REVIEWED',$2)
            """, target_id, teacher)
            during_pause = await connection.fetchrow("""
                SELECT s.revision,s.content_json,s.current_revision_id,r.revision_no,
                       (SELECT count(*) FROM submission_revisions x
                         WHERE x.submission_id=s.id AND x.revision_no=1) AS baseline_count,
                       (SELECT count(*) FROM submission_revisions x
                         WHERE x.submission_id=s.id AND x.revision_no=2) AS current_count,
                       rv.submission_revision_id,rv.association_provenance
                  FROM student_submissions s
                  JOIN submission_revisions r ON r.id=s.current_revision_id
                  JOIN submission_reviews rv ON rv.submission_id=s.id
                 WHERE s.id=$1
            """, target_id)
            assert during_pause["baseline_count"] == during_pause["current_count"] == 1
            assert during_pause["revision"] == during_pause["revision_no"] == 2
            assert during_pause["content_json"] == "legacy-during-pause"
            assert during_pause["submission_revision_id"] == during_pause["current_revision_id"]

            # Hold a second legacy write open while the resumed worker processes
            # batches. Its row lock forces SKIP LOCKED; release it only after a
            # later batch has committed, so the committed writer is concurrent
            # with the worker process rather than merely before/after it.
            overlap_id = await connection.fetchval(
                "SELECT id FROM student_submissions ORDER BY id DESC OFFSET 1 LIMIT 1"
            )
            writer = await asyncpg.connect(dsn(database))
            tx = writer.transaction()
            await tx.start()
            await writer.execute("""
                UPDATE student_submissions
                   SET status='REVIEWED',revision=2,content_json='legacy-during-resume',submitted_at=now()
                 WHERE id=$1
            """, overlap_id)
            worker_env = os.environ.copy()
            worker_env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
            worker_env["GATE738E_DISPOSABLE"] = "1"
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-B", "scripts/backfill_submission_revisions.py",
                "--batch-size", "25", "--idle-timeout-seconds", "10",
                cwd=ROOT, env=worker_env, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            progress = False
            for _ in range(300):
                await asyncio.sleep(.05)
                progress = await connection.fetchval(
                    "SELECT processed_submissions > 25 FROM submission_revision_backfill_state WHERE singleton=true"
                )
                if progress:
                    break
                if process.returncode is not None:
                    break
            assert progress and process.returncode is None, "resumed worker did not progress around a locked row"
            await tx.commit()
            await writer.close()
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            if process.returncode:
                raise RuntimeError((stdout + stderr).decode(errors="replace")[-2500:])

            overlap = await connection.fetchrow("""
                SELECT s.revision,s.content_json,r.revision_no,
                       (SELECT count(*) FROM submission_revisions x
                         WHERE x.submission_id=s.id AND x.revision_no=1) AS baseline_count,
                       (SELECT count(*) FROM submission_revisions x
                         WHERE x.submission_id=s.id AND x.revision_no=2) AS current_count
                  FROM student_submissions s
                  JOIN submission_revisions r ON r.id=s.current_revision_id
                 WHERE s.id=$1
            """, overlap_id)
            assert overlap["baseline_count"] == overlap["current_count"] == 1
            assert overlap["revision"] == overlap["revision_no"] == 2
            assert overlap["content_json"] == "legacy-during-resume"

            validated = await connection.fetchrow(
                "SELECT status,processed_submissions FROM submission_revision_backfill_state WHERE singleton=true"
            )
            assert validated["status"] == "VALIDATED"
            before_replay = await connection.fetchrow("""
                SELECT (SELECT count(*) FROM submission_revisions) AS revisions,
                       (SELECT count(*) FROM submission_reviews) AS reviews,
                       (SELECT count(*) FROM student_submissions s WHERE s.status IN ('SUBMITTED','REVIEWED')
                          AND NOT EXISTS (SELECT 1 FROM submission_revisions r WHERE r.id=s.current_revision_id
                            AND r.submission_id=s.id AND r.tenant_id=s.tenant_id AND r.revision_no=s.revision)) AS invalid_parents,
                       (SELECT count(*) FROM submission_reviews rv WHERE rv.submission_revision_id IS NULL
                          OR NOT EXISTS (SELECT 1 FROM submission_revisions r WHERE r.id=rv.submission_revision_id
                            AND r.submission_id=rv.submission_id AND r.tenant_id=rv.tenant_id)) AS invalid_reviews
            """)
        finally:
            await connection.close()

        # Running the actual worker after VALIDATED performs a full validation
        # replay and must be row-idempotent.
        command([sys.executable, "-B", "scripts/backfill_submission_revisions.py",
                 "--batch-size", "25", "--idle-timeout-seconds", "10"], database)
        connection = await asyncpg.connect(dsn(database))
        try:
            after_replay = await connection.fetchrow("""
                SELECT (SELECT count(*) FROM submission_revisions) AS revisions,
                       (SELECT count(*) FROM submission_reviews) AS reviews,
                       (SELECT count(*) FROM student_submissions s WHERE s.status IN ('SUBMITTED','REVIEWED')
                          AND NOT EXISTS (SELECT 1 FROM submission_revisions r WHERE r.id=s.current_revision_id
                            AND r.submission_id=s.id AND r.tenant_id=s.tenant_id AND r.revision_no=s.revision)) AS invalid_parents,
                       (SELECT count(*) FROM submission_reviews rv WHERE rv.submission_revision_id IS NULL
                          OR NOT EXISTS (SELECT 1 FROM submission_revisions r WHERE r.id=rv.submission_revision_id
                            AND r.submission_id=rv.submission_id AND r.tenant_id=rv.tenant_id)) AS invalid_reviews
            """)
            assert dict(after_replay) == dict(before_replay)
            assert after_replay["invalid_parents"] == 0 and after_replay["invalid_reviews"] == 0
            print(json.dumps({
                "interrupted_worker": "PASS (one committed batch; state RUNNING)",
                "legacy_write_during_pause": "PASS (baseline, current pointer, and review linked)",
                "resume_with_concurrent_legacy_writer": "PASS (SKIP LOCKED progress; snapshot integrity)",
                "validated_replay": "PASS (counts and integrity unchanged)",
                "backfill_state": dict(validated),
                "rows_before_replay": dict(before_replay),
                "rows_after_replay": dict(after_replay),
                "verdict": "PASS",
            }, default=str, indent=2))
        finally:
            await connection.close()
    finally:
        admin = await asyncpg.connect(ADMIN_DSN)
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        finally:
            await admin.close()


if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")
