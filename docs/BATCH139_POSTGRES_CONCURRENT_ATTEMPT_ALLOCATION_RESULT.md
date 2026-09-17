# Gate 139 — PostgreSQL Concurrent Attempt Allocation Qualification

Date: 2026-09-17
Mode: Read-only qualification; no Docker/server/schema changes.

## Result

Status: BLOCKED_NO_POSTGRES_HARNESS

The repository contains no runnable PostgreSQL harness available in the current local environment. `psql` is not installed and TCP connectivity to `127.0.0.1:5432` is unavailable. Per Commander instruction, no Docker or infrastructure was started or created.

## Required scenario

Not executed: two genuinely concurrent `start_attempt` calls for the same student and assignment, repeated iterations, rollback observation, and two different students on one assignment.

## Code evidence

`start_attempt` currently allocates `MAX(attempt_no)+1` and relies on a unique constraint `(assignment_id, student_id, attempt_no)`. This is insufficient to claim race-free allocation without PostgreSQL concurrency evidence.

## Production mutation

NONE. No server, SSH, Docker, database, migration, schema, environment, or deployment operation was performed.

## Decision

Gate 139 remains blocked until an existing disposable PostgreSQL harness is made accessible. Do not change the allocation algorithm or create new infrastructure in this Gate.
