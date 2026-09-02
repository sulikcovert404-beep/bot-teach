# Admin Content Pipeline — Current-State Audit

**Status:** review-only; no runtime or migration changes.

## Evidence reviewed

- `docs/ADMIN_CONTENT_PIPELINE_PRD.md`
- `app/db/models.py`
- `app/services/document_ingestion.py`
- `app/services/vector_store.py`
- `app/services/rag.py`
- curriculum and source route tests

## Findings

### Already aligned

- Stable `source_id`, `content_hash`, embedding model, and index-generation concepts exist in the current source and RAG boundaries.
- Ingestion rejects empty identifiers and protects URI validation; duplicate source handling is covered by the ingestion path.
- RAG citations preserve source/chunk/page provenance, and vector search records the embedding model.
- Curriculum writes and source ingestion have role/authentication and audit-related test coverage.

### Gaps before implementation approval

1. The PRD lifecycle (`pending`, `review`, `approved`, `rejected`, `failed`, `archived`) is not represented as a persisted content-version state machine in the current models.
2. `SourceDocument` currently has limited source metadata; book/grade/subject/curriculum edition and parser/index generations need an explicit versioned ownership model before retrieval filtering can be guaranteed.
3. Existing ingestion creates deterministic chunks, but the PRD's parser version, page range, chapter/lesson linkage, and publication generation are not all persisted as first-class fields.
4. Audit records exist, but the PRD needs transition-specific invariants: actor role, previous state, next state, reason, timestamp, and idempotency key.
5. Rollback semantics require an immutable version plus an atomic publication pointer; deleting or mutating the current document would not satisfy the stated rollback requirement.
6. Embedding/index publication needs an explicit failure state and retry contract so a successfully parsed source cannot become visible before its approved index is ready.

## Recommended Commander decisions

- Approve the lifecycle transition table and immutable source-version model.
- Decide whether `book_id` and `curriculum_version` are mandatory for every educational source.
- Decide allowed URI/file types, retention of rejected versions, and publication/embedding scheduling.
- Require tests for transition authorization, idempotency, rejected/archived retrieval exclusion, rollback, parser failure visibility, and Persian/OCR metadata.

## Validation status

This audit is advisory and does not claim that the pipeline is implemented. The PGVector benchmark remains blocked by staging connectivity; this document is independent of that blocker.

Current independent evidence:

- Full test suite in the refreshed Docker image: `137 passed`.
- mypy strict check for `app`: `65 source files`, no issues.
- Ruff `F` checks for the application: passed.
- FastAPI import/startup smoke: application loaded with 23 routes.
- Migration remains blocked by PostgreSQL volume authentication (`InvalidPasswordError`), so database-backed lifecycle behavior is not yet validated.

## PostgreSQL blocker decision record

The failure is an authentication mismatch between the configured connection and the
existing Docker volume. The safe recovery choices are:

1. **Retain the volume:** obtain the credential that was used when the volume was
   initialized, update the runtime connection configuration through the secret
   management path, then rerun migration and health smoke tests.
2. **Rebuild the volume:** only after Commander confirms that the staging data is
   disposable and any required backup has been verified; recreate the database,
   run migrations, and repeat the smoke tests.

No benchmark result should be reported until one of these choices succeeds and the
database identity, migration status, and PGVector extension are recorded as evidence.
