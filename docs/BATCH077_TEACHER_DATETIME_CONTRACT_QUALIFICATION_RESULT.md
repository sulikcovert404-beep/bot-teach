# BATCH077 — Teacher Datetime Contract Qualification Result

Mode: read-only; no datetime replacement, schema/migration, test edits, dependency upgrade, suppression, or operational change.

## Data flow
- `app/api/routes/teacher.py:498`: sets `Assignment.publish_at` when publishing, then commits and serializes via `_assignment_payload` (`isoformat`).
- `app/api/routes/teacher.py:508`: sets `Assignment.close_at` when closing, then commits and serializes via `_assignment_payload`.
- `app/db/models.py:1882,1884`: both columns are `DateTime(timezone=True)`, nullable.
- Student and exam services compare these values after explicit UTC normalization (`replace(tzinfo=timezone.utc)` in relevant paths); API payloads use ISO-8601.

## Contract assessment
Current runtime uses naive `datetime.utcnow()` values written to timezone-aware columns. Existing tests pass with this behavior and establish the current contract. Replacing with `datetime.now(timezone.utc)` would make values aware at assignment time and may alter SQLAlchemy normalization, comparisons, and serialized offsets. A schema/API compatibility decision is required before changing it.

## Focused existing tests
- `tests/test_mvp_pilot_http_lesson_access.py::test_pilot_http_assignment_publish_and_student_access` exercises publish/close and access behavior and currently passes.
- Assignment contract/persistence tests also pass in the latest full run.

## Safe-change recipe (future gate)
Before replacing the calls, qualify SQLite/PostgreSQL round-trip behavior, API timestamp shape, naive/aware comparisons, and before/after publish/close access. If all consumers are standardized on aware UTC, use `datetime.now(timezone.utc)` (or `datetime.now(datetime.UTC)` on supported Python) with focused regression tests. Otherwise introduce an explicit compatibility boundary without changing schema implicitly.

## Result
Exact data flow identified; DB columns are timezone-aware; downstream code normalizes comparisons; API emits ISO-8601. No migration or code change is justified in this Gate. Test gap: no dedicated test asserts timezone awareness/offset shape after persistence; add only under a future approved test gate.

Commit Gate 077: HOLD pending Commander approval.
