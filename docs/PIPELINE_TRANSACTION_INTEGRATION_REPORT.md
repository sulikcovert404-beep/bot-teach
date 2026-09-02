# PIPELINE TRANSACTION INTEGRATION REPORT

## Scope
Advisory review before implementation of the pipeline service transaction boundary integration. No code changes are authorized by this report.

## Agent responses

### Gemini — transaction architecture
Strengths: atomic state promotion plus outbox, CAS version checks, and PublicationPointer separation. Risks: external I/O inside database transactions, CAS zero-row ambiguity, pointer integrity, outbox contention, and migration safety. Recommendations: isolate external work from a short prepare/commit transaction; enforce rowcount=1 and explicit concurrency errors; add pointer FKs/integrity checks, idempotency, rollback tests, and dialect-aware migration tests.

### Qwen — implementation strategy
Strengths: orthogonal lifecycle states, transactional outbox, strict idempotency fields, and immutable provenance. Risks: publication invariant not enforced at the database/write boundary, missing vector deletion and retention lifecycle, OCR BiDi nondeterminism, polling latency, and provider sync ambiguity. Recommendations: guard publication on VALIDATED + APPROVED + VECTOR_SYNCED, add explicit sync status and cleanup events, deterministic extraction, tombstoning, strict event types, and provider-neutral adapter contracts.

### GLM — alternative consistency review
Strengths: a single DB transaction around state/pointer/history/outbox/idempotency, CAS, and provider-neutral boundaries. Critical risks: incomplete atomic unit, ambiguous commit retries, TOCTOU guards, approval revocation races, rollback representation, missing blob registry/read-back verification, mock-only tests, and migration races. Recommendations: enumerate all writes and fixed lock order; fold guards into CAS WHERE clauses; probe idempotency after ambiguous commit; lock approval rows; represent rollback as a new version; test side effects against a real RDBMS; use expand/contract migrations and invariant checks.

## Common points
- Keep external storage/vector calls outside the database transaction.
- Make state, publication pointer, history, outbox, and idempotency persistence one explicit atomic unit.
- Use monotonic version CAS and distinguish concurrency, illegal transition, and missing-row outcomes.
- Add commit/rollback, duplicate delivery, crash/ambiguous commit, and concurrent publish tests.
- Preserve provider-neutral service boundaries and test adapters against hostile delivery/order behavior.
- Treat Persian RTL/LTR OCR determinism, canonical UTF-8/ZWNJ handling, and migration backfill as correctness concerns.

## Conflicts and tradeoffs
- Gemini allows READ COMMITTED with explicit CAS/locks; GLM emphasizes documenting isolation and locking approval rows, with SERIALIZABLE only if needed. Recommendation: start with READ COMMITTED plus guard-in-WHERE and explicit row locks, then prove with contention tests.
- Qwen favors polling/notification improvements; GLM says notification may optimize latency but polling must remain the correctness baseline. Recommendation: keep relay correctness independent of wake-up mechanism.
- GLM recommends rollback-as-new-version to preserve monotonic ordering; this should be adopted before VectorSync semantics are implemented.

## Codex validation
The repository already contains lifecycle guard models/migration artifacts and focused guard tests. The current scope has not yet implemented the transaction service boundary. PostgreSQL/PGVector staging remains blocked by the existing credential/connectivity issue, so real-RDBMS contract execution is pending. No secrets or private data were included in the handoff.

## Recommendation
Conditional approval for design refinement only. Before implementation, finalize the atomic-unit write list, monotonic CAS and rowcount error contract, approval-locking rule, rollback-as-new-version semantics, vector deletion/retraction acknowledgment, and real-RDBMS fault-injection test plan. Do not implement until Commander explicitly approves this report and the resulting design.

## Commander decision required
Approve or reject the proposed transaction-boundary design and the listed pre-implementation gates. No implementation has been performed.

## Final design refinement checkpoint

### Updated contracts
- Atomic write set: ContentVersion state, PublicationPointer, approval snapshot reference, outbox event, idempotency record, and audit history commit together in one short database transaction.
- External I/O is forbidden inside that transaction: OCR, embedding APIs, external storage, and agent/API calls remain outside it.
- Publication uses database guarded CAS: update the pointer only when `current_version_id = expected_version`; require rowcount exactly 1. Rowcount 0 is a conflict/concurrent-update outcome requiring bounded retry or explicit failure.
- Publication gate requires VALIDATED + APPROVED + VECTOR_SYNCED + matching digest and a traceable approval snapshot.
- Ambiguous commit retries probe the idempotency key, event identity, and transaction history before repeating work.
- Approval is locked/snapshotted for the publish transaction to prevent revocation races.
- Rollback is non-destructive: retire the current version and create a new corrected/rollback version; never delete the published record in place.
- Future schema evolution follows Expand → Migrate → Contract with no destructive migration.

### Unresolved decisions
- Exact persistence schema for audit history and approval snapshot reference.
- Concrete exception taxonomy for CAS rowcount-0 (conflict vs missing vs illegal state).
- Database engine used for contract tests while PostgreSQL staging remains unavailable.
- Relay ordering/sequence field details and bounded retry policy.

### Implementation scope after checkpoint
Only service transaction boundary, real CAS integration, PublicationPointer persistence flow, outbox persistence contract tests, and rollback/failure tests. No ingestion, OCR/parser, upload, production dispatcher, PGVector changes, deployment, or production migration.

### Test plan
- Atomic commit and rollback at each write point.
- Concurrent publish and CAS conflict with exactly one winner.
- Duplicate and ambiguous-commit retry using idempotency/event identity.
- Approval-lock race and digest mismatch rejection.
- Rollback-as-new-version behavior.
- Partial failure leaves no pointer/outbox/idempotency half-state.
- UTF-8/ZWNJ/RTL-LTR metadata round trips.
- Migration safety/invariant checks and regression suite.
