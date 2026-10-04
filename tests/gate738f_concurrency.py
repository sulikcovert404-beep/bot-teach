"""Synthetic writer/backfill overlap probe. Requires the Gate738F disposable PG only."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")

PORT = int(os.environ["GATE738E_LOCAL_PG_PORT"])
assert os.environ.get("GATE738F_DISPOSABLE") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def migration(db: str, rev: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}"
    p = subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", rev], cwd=ROOT,
                       env=env, capture_output=True, text=True, timeout=180, check=False)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])


async def main() -> None:
    db = "gate738e_" + uuid4().hex
    admin = await asyncpg.connect(host="127.0.0.1", port=PORT, user="gate738e", database="gate738e_test")
    await admin.execute(f'CREATE DATABASE "{db}"')
    await admin.close()
    migration(db, "20260921_0022")
    c = await asyncpg.connect(host="127.0.0.1", port=PORT, user="gate738e", database=db)
    teacher = await c.fetchval("INSERT INTO users(role) VALUES('TEACHER') RETURNING id")
    tp = await c.fetchval("INSERT INTO teacher_profiles(teacher_id,tenant_id) VALUES($1,'race') RETURNING id", teacher)
    room = await c.fetchval("INSERT INTO classrooms(classroom_key,tenant_id,teacher_profile_id) VALUES('race','race',$1) RETURNING id", tp)
    assignment = await c.fetchval("INSERT INTO assignments(teacher_id,classroom_id,tenant_id,title,status) VALUES($1,$2,'race','race','PUBLISHED') RETURNING id", teacher, room)
    user0 = await c.fetchval("SELECT coalesce(max(id),0)+1 FROM users")
    n = 5000
    await c.execute("INSERT INTO users(id,role) SELECT $1+g,'STUDENT' FROM generate_series(0,$2-1) g", user0, n)
    await c.execute("SELECT setval('users_id_seq',GREATEST((SELECT max(id) FROM users),1))")
    await c.execute("INSERT INTO student_profiles(student_id) SELECT $1+g FROM generate_series(0,$2-1) g", user0, n)
    p0 = await c.fetchval("SELECT min(id) FROM student_profiles WHERE student_id >= $1", user0)
    await c.execute("""
      INSERT INTO student_submissions(assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
      SELECT $1,$2+g,'race','SUBMITTED',1,'{\"version\":1}',now() FROM generate_series(0,$3-1) g
    """, assignment, p0, n)
    await c.close()
    for rev in ("20261003_0027", "20261003_0028", "20261003_0029"):
        migration(db, rev)
    c = await asyncpg.connect(host="127.0.0.1", port=PORT, user="gate738e", database=db)

    env = os.environ.copy()
    env["DATABASE_URL"] = f"postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}"
    env["GATE738E_DISPOSABLE"] = "1"
    # A high-id parent stays outside the first bounded batch while the worker
    # and legacy writers run concurrently on the same expanded database.
    locked_id = await c.fetchval("SELECT id FROM student_submissions ORDER BY id DESC LIMIT 1")
    started = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-B", "scripts/backfill_submission_revisions.py",
        "--batch-size", "100", "--idle-timeout-seconds", "2", "--max-batches", "20",
        cwd=ROOT, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )

    state = None
    for _ in range(200):
        await asyncio.sleep(.05)
        state = await c.fetchrow("SELECT status,processed_submissions FROM submission_revision_backfill_state")
        if state["processed_submissions"] >= 100:
            break
        if proc.returncode is not None:
            raise RuntimeError("bounded backfill exited before overlap writes")
    if not state or state["processed_submissions"] < 100:
        raise RuntimeError(f"backfill did not progress: {state}")
    worker_alive_during_overlap = proc.returncode is None
    if not worker_alive_during_overlap:
        raise RuntimeError("backfill worker was no longer running at overlap write point")

    # Concurrent legacy update of an unprocessed parent, then reviews on both
    # an already-backfilled and a not-yet-backfilled parent.
    await c.execute("""
      UPDATE student_submissions SET status='REVIEWED',revision=2,
             content_json='{"version":2}',submitted_at=now() WHERE id=$1
    """, locked_id)
    await c.execute("""
      INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
      VALUES($1,'race','REVIEWED',$2)
    """, locked_id, teacher)
    migrated_id = await c.fetchval("SELECT id FROM student_submissions WHERE current_revision_id IS NOT NULL AND id<>$1 ORDER BY id LIMIT 1", locked_id)
    await c.execute("""
      INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
      VALUES($1,'race','REVIEWED',$2)
    """, migrated_id, teacher)

    new_user = await c.fetchval("INSERT INTO users(role) VALUES('STUDENT') RETURNING id")
    new_profile = await c.fetchval("INSERT INTO student_profiles(student_id) VALUES($1) RETURNING id", new_user)
    new_submission = await c.fetchval("""
      INSERT INTO student_submissions(assignment_id,student_id,tenant_id,status,revision,content_json,submitted_at)
      VALUES($1,$2,'race','SUBMITTED',1,'{\"new\":true}',now()) RETURNING id
    """, assignment, new_profile)
    await c.execute("""
      INSERT INTO submission_reviews(submission_id,tenant_id,review_status,reviewed_by)
      VALUES($1,'race','REVIEWED',$2)
    """, new_submission, teacher)
    await c.close()

    _, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=30)
    stderr = stderr_bytes.decode(errors="replace")
    pause_rc = proc.returncode
    partial_elapsed = time.perf_counter() - started
    c = await asyncpg.connect(host="127.0.0.1", port=PORT, user="gate738e", database=db)
    locked = await c.fetchrow("""
      SELECT s.status,s.revision,s.content_json,s.current_revision_id,r.revision_no,r.content_json AS snapshot,
             (SELECT count(*) FROM submission_reviews rv WHERE rv.submission_id=s.id AND rv.submission_revision_id IS NULL) AS unlinked
        FROM student_submissions s LEFT JOIN submission_revisions r ON r.id=s.current_revision_id
       WHERE s.id=$1
    """, locked_id)
    assert pause_rc != 0 and "BACKFILL_PAUSED" in stderr
    assert locked["revision"] == 2 and locked["revision_no"] == 2 and locked["content_json"] == locked["snapshot"]
    assert locked["unlinked"] == 0
    # Exact evidence: the previous revision 1 did not get a baseline snapshot
    # because the legacy update won before the backfill reached this row.
    prior_snapshot_count = await c.fetchval("SELECT count(*) FROM submission_revisions WHERE submission_id=$1 AND revision_no=1", locked_id)
    assert prior_snapshot_count == 0
    assert await c.fetchval("SELECT current_revision_id IS NOT NULL FROM student_submissions WHERE id=$1", migrated_id)
    assert await c.fetchval("SELECT submission_revision_id IS NOT NULL FROM submission_reviews WHERE submission_id=$1", migrated_id)
    assert await c.fetchval("SELECT submission_revision_id IS NOT NULL FROM submission_reviews WHERE submission_id=$1", locked_id)
    assert await c.fetchval("SELECT count(*) FROM submission_revisions WHERE submission_id=$1", new_submission) == 1
    assert await c.fetchval("SELECT count(*) FROM submission_reviews WHERE submission_id=$1 AND submission_revision_id IS NOT NULL", new_submission) == 1
    await c.close()

    env["GATE738E_DISPOSABLE"] = "1"
    start_resume = time.perf_counter()
    resumed = await asyncio.create_subprocess_exec(
        sys.executable, "-B", "scripts/backfill_submission_revisions.py", "--batch-size", "300",
        "--idle-timeout-seconds", "2", cwd=ROOT, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, resumed_stderr = await asyncio.wait_for(resumed.communicate(), timeout=180)
    if resumed.returncode:
        raise RuntimeError(resumed_stderr.decode(errors="replace")[-3000:])
    resumed_seconds = time.perf_counter()-start_resume
    migration(db,"20261003_0030")
    migration(db,"20261003_0031")
    c = await asyncpg.connect(host="127.0.0.1", port=PORT, user="gate738e", database=db)
    final = await c.fetchrow("""
      SELECT (SELECT count(*) FROM student_submissions WHERE current_revision_id IS NULL) missing_parent,
             (SELECT count(*) FROM submission_reviews WHERE submission_revision_id IS NULL) unlinked_review,
             (SELECT count(*) FROM submission_revisions WHERE submission_id=$1) locked_revision_count,
             (SELECT count(*) FROM submission_revisions) revision_count
    """, locked_id)
    await c.close()
    assert final["missing_parent"] == 0 and final["unlinked_review"] == 0
    print({"database":db,"total_submissions":n+1,"worker_alive_during_overlap":worker_alive_during_overlap,
           "paused_exit_code":pause_rc,"partial_backfill_seconds":round(partial_elapsed,3),
           "partial_state_before_writes":dict(state),"locked_parent":dict(locked),"missing_old_revision1_snapshot":prior_snapshot_count,
           "resume_seconds":round(resumed_seconds,3),"final_integrity":dict(final),"backfill_resume":"PASS",
           "concurrent_write_consistency":"PASS_FOR_CURRENT_POINTERS_REVIEWS_AND_NEW_SUBMISSION",
           "old_revision_1_snapshot_rows":prior_snapshot_count,
           "historical_baseline_preservation":"FAIL_FOR_UNPROCESSED_ROW_UPDATED_DURING_BACKFILL"})


if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")
