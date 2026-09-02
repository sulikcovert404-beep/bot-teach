# CURRICULUM PIPELINE IMPLEMENTATION READINESS REPORT

Status: advisory review complete; no implementation or schema migration performed.

## Scope and evidence
The review covered the sanitized handoff for the approved Curriculum Pipeline Contract Specification. Security scan reported `SECRET_SCAN: no matching credential patterns`. Existing independent validation remains `12 passed` for retrieval benchmark/dataset/evaluation tests. Real PGVector staging execution remains blocked by PostgreSQL credential/volume mismatch; no benchmark result was fabricated.

## Agent responses

### Gemini — architecture and evaluation strategy
Recommended staged implementation with separate ProcessingState and ReviewState, an atomic PublicationPointer, transactional outbox, explicit vector synchronization state, immutable provenance/digests, shared versioned Persian normalization, and provider-neutral contracts. Emphasized canonical source identity, deterministic processing, and retrieval visibility only through the published pointer.

### Qwen — implementation and migration feasibility
Confirmed the dual-state model, pointer/outbox boundary, SHA-256 provenance, idempotency, and source identity as feasible. Highlighted logical-vs-versioned entity separation, migration/FK compatibility, tombstoning/garbage collection, vector cleanup on rejection/rollback, typed-block embedding policy, deterministic RTL/LTR OCR handling, and tests for retries and partial failure.

### GLM — alternative design and consistency review
Supported a relational pointer plus transactional outbox with CAS/version checks. Recommended explicit lifecycle orthogonality, rollback/unpublish semantics, idempotency at upload/processing/publication layers, versioned normalization in the digest, blocks-to-chunks modeling, provider protocols, quarantine/resource limits, and pointer-resolved retrieval. The current primary GLM tab stalled after one refresh; the approved fallback GLM conversation supplied the completed compatible review.

### Claude — sensitive data-integrity/security review
Used only for migration, security, and data-integrity risks. Identified the need for pointer-resolved retrieval, deterministic OCR metadata, upload idempotency, exclusion of failed/processing rows, snapshot-consistent pointer reads, vector cleanup on rollback, parser isolation, magic-byte/polyglot checks, licensing/provenance metadata, and pinned normalization. It also noted that PGVector claims require environment evidence before production interpretation.

## Common points
1. Keep ProcessingState and ReviewState separate; approval is human-controlled.
2. Publish only after validation, approval, and vector synchronization; resolve retrieval through one atomic pointer.
3. Use immutable ContentVersion records, canonical Source IDs, content/pipeline digests, and shared versioned Persian normalization.
4. Make upload and outbox handling idempotent, retry-safe, observable, and compatible with rollback/unpublish.
5. Preserve provider-neutral VectorStore/Retriever boundaries and define typed-block/embedding behavior explicitly.
6. Test migration compatibility, partial failure, rejected versions, vector deletion, OCR nondeterminism, and Persian RTL/LTR/ZWNJ cases.

## Conflicts and reconciliation
- Gemini/Qwen/GLM suggested richer future typed-block routing and additional vector states. Commander approved `EmbeddingRouter` as a contract-level extension while allowing V1 to support text concretely; this report treats it as a contract concern, not immediate production OCR/embedding work.
- Agents proposed polling alternatives such as LISTEN/NOTIFY/CDC. Commander’s accepted contract requires a transactional outbox; delivery mechanism remains an implementation choice and must not weaken atomicity.
- Agents suggested garbage collection and broader lifecycle states. These are recorded as requirements for a later retention design; the foundation must first preserve immutable history and safe rollback.

## Codex validation
The handoff was sanitized and pushed as commit `b2c31ae` (`chore: add curriculum pipeline implementation readiness handoff`). Retrieval tests pass (`12 passed in 0.11s`). No schema/migration implementation was made during this review. PGVector remains `WAITING_FOR_ENVIRONMENT`.

## Recommendation
Proceed only with the approved Implementation Foundation: additive lifecycle models/contracts, non-destructive migration scaffolding, PublicationPointer, transactional outbox, provenance/hash, idempotency, canonical source identity, and focused tests. Keep OCR production, parser production, upload UI, full ingestion, automatic publish, destructive cleanup, and deployment out of scope. Obtain Commander approval before any schema or migration implementation.

## Commander decision required
Approve or reject the Implementation Foundation scope and sequencing above. Agent output is advisory only.
