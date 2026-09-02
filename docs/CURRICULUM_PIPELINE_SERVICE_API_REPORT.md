# CURRICULUM PIPELINE SERVICE API REPORT

## Completed

- Added `app/services/curriculum_pipeline_api.py` as a provider-neutral service boundary.
- Separated lifecycle commands from query methods for content status and processing jobs.
- Added staged flow: `Validate -> Approve -> Vector Sync -> Publish`; publish never triggers vector sync.
- Added role-aware operation policy, typed errors, expected-version CAS checks, idempotent command receipts, and asynchronous `job_id` receipts.
- Preserved immutable content digest and digest checks at approval and vector-sync boundaries.
- Added retirement as a non-destructive state transition.
- Added independent tests for invalid transitions, authorization, digest mismatch, idempotency, CAS conflicts, staged gating, and async jobs.

## Validation

- `python -m pytest tests/test_curriculum_pipeline_api.py -q`: **5 passed**
- `python -m compileall -q app`: passed
- `git diff --check`: passed

## Scope exclusions

No OCR, parser, real upload, production worker, vector runtime, Telegram UI, or deployment changes were made. The in-memory reference service is an adapter contract; database/HTTP adapters remain a subsequent implementation layer.

## Remaining

- Add persistence and HTTP adapters against the approved database transaction boundary.
- Resolve real PostgreSQL validation when staging is available.
