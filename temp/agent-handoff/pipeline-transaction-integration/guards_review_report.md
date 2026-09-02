# AI TEAM REVIEW REPORT — CURRICULUM PIPELINE CONTRACT GUARDS

Status: advisory review only; no implementation performed.

## Agent responses

### Gemini — Architecture guard review
The request returned an error after submission and did not produce a usable guard-specific review. Gemini's earlier architecture reviews consistently recommended explicit legal transition matrices, digest-bound approvals, atomic pointer/CAS publication, vector synchronization gates, idempotent semantic keys, and Persian normalization/versioning. These earlier findings are context only and are not treated as a completed review of the current files.

### Qwen — Implementation/test strategy
Qwen reviewed the sanitized foundation handoff and found the additive migration, orthogonal processing/review/vector lifecycle modeling, transactional outbox fields, ingestion idempotency records, and provenance digests strong foundations. Qwen identified the main implementation gap as missing enforcement: publication must require `VALIDATED + APPROVED + VECTOR_SYNCED`; state transitions need explicit guards and tests; vector deletion/rollback events, retry/DLQ semantics, tombstoning/retention, strict event types, provider-neutral sync status, typed-block routing, and deterministic Persian STEM/OCR handling need explicit contracts.

### GLM — Consistency/edge-case review
GLM received the prompt but reported that it could not fetch the GitHub Raw files, so it declined to claim a code review. It supplied a useful verification checklist: legal transition matrix and fail-closed unknown states; atomic pointer/CAS and digest equality; semantic idempotency and duplicate/out-of-order delivery tests; no provider-specific imports in guard logic; explicit rollback/retraction compensation and deletion acknowledgement; and preservation of Persian ZWNJ/digit/diacritic policies with versioned curriculum taxonomy. This is a limitation report, not a validated implementation finding.

## Common points
1. Guard publication atomically and require processing validation, editorial approval, and vector synchronization.
2. Model legal transitions as data and test them, including unknown/invalid states and race/CAS behavior.
3. Bind approval and publication to immutable content version/digest; use semantic idempotency keys rather than request IDs alone.
4. Define outbox delivery, retries, duplicate/out-of-order behavior, dead-letter handling, and rollback/vector deletion semantics.
5. Keep guard logic provider-neutral and make vector sync status an explicit adapter contract.
6. Preserve Persian ZWNJ and version normalization; cover mixed RTL/LTR math, digits, OCR noise, and curriculum-version metadata.

## Conflicts
- Gemini did not complete a usable current review because the request errored.
- GLM could not inspect Raw URLs and therefore gave a checklist rather than file-specific findings.
- Qwen's review is the only current file-grounded review; its recommendations must still be validated against repository code and tests.

## Codex validation
Current repository validation from the foundation milestone: additive migration applied successfully on temporary SQLite; full test suite passed (`137 passed, 1 warning`); migration head is `f7a8b9c0d1e2`. No guard implementation or production ingestion/vector benchmark work has been performed. The current models expose lifecycle fields and outbox/idempotency persistence, but business-transition enforcement is not yet implemented.

## Recommendation
Prepare a small provider-neutral guard service and contract tests only after Commander approval. First define transition tables and publication invariants, then implement fail-closed guards, digest/CAS checks, idempotency and outbox duplicate semantics, and rollback/delete event contracts. Keep ingestion, OCR/parser, dispatcher productionization, PGVector execution, and deployment out of this milestone.

## Commander decision required
Approve or reject implementation of the scoped `CURRICULUM PIPELINE CONTRACT GUARDS` milestone. No code changes should be made from agent advice alone.
