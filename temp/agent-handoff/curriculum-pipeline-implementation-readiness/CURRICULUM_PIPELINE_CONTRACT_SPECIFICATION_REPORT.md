# CURRICULUM PIPELINE CONTRACT SPECIFICATION REPORT

Status: advisory review complete; no production implementation performed.

## Proposed formal contracts

- ProcessingState: `UPLOADED`, `PROCESSING`, `EXTRACTED`, `CHUNKED`, `EMBEDDING`, `VECTOR_SYNCING`, `VECTOR_SYNCED`, `VALIDATED`, `FAILED`, `QUARANTINED`.
- ReviewState: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `RETIRED`.
- PublicationPointer: one relational current-version pointer per logical source, changed with compare-and-swap; pointer history, audit row, and transactional outbox event commit atomically. Public retrieval resolves only the published pointer.
- VectorSync: `VECTOR_PENDING -> VECTOR_SYNCING -> VECTOR_SYNCED` or `VECTOR_FAILED`; publication requires `VALIDATED + APPROVED + VECTOR_SYNCED`.
- Provenance: logical source, edition/grade/subject/chapter/lesson, page range, structural path, parser/OCR and normalizer versions, embedding model and index generation.
- Hashes: SHA-256 source, extracted, and canonical chunk payloads; pipeline digest covers source hash, parser, OCR, normalizer, chunker, and configuration versions. Record hash algorithm and canonical serialization.
- Persian normalization: one shared, pinned, versioned policy used at ingestion, retrieval, and evaluation; include Arabic/Persian glyphs, digits, ZWNJ, tatweel, punctuation and BiDi rules.
- Parser/OCR boundary: isolated asynchronous workers, no network or script execution, restricted filesystem, magic-byte and polyglot checks, decompression/resource limits, quarantine for security failures, and recorded parser/OCR versions.
- Source IDs: canonical externally stable `book:edition:page:chunk` form, with deterministic generation and alignment to evaluation fixtures.
- Outbox: versioned event envelope with idempotency key, aggregate/version ID, event type, payload hash, retry/dead-letter state, and consumer acknowledgement.

## Agent responses

### Gemini — architecture validation

Recommended edition/year and hierarchical targets in the dataset, disjunctive multi-chunk ground truth, R-Precision/MAP/NDCG for multi-hop cases, explicit citation-entailment separate from faithfulness, deterministic Persian normalization, and stratified benchmark slices. It endorsed provider-neutral retriever contracts and a Source Guardian confusion matrix.

### Qwen — implementation feasibility

Endorsed orthogonal processing/review states, transactional outbox plus publication pointer, explicit vector synchronization, idempotency keys, EmbeddingRouter for typed blocks, parent-context injection, asynchronous `202` processing, deterministic RTL/LTR STEM extraction, and migration-first planning. It highlighted rollback embedding validity and graceful fallback behavior.

### GLM — alternative design

Recommended relational pointer plus transactional outbox with CAS, explicit unpublish/retire, bounded retention/tombstones, canonical typed-block serialization, normalization version and hash algorithm in fingerprints, provider-neutral parser/OCR interfaces, quarantine, OCR confidence, and pointer-resolved retrieval. GLM also emphasized alignment between external source IDs and benchmark fixtures.

### Claude — sensitive security/data-integrity review

Claude noted that the draft was supplied as a contract description rather than an implementation diff, so its review is design-level. It requires explicit retrieval routing through the publication pointer, deterministic OCR metadata and drift handling, upload idempotency, structural exclusion of failed/processing rows, single-snapshot pointer reads, embedding validity on rollback, detailed PDF isolation controls, magic-byte/polyglot rejection, fetch-time SSRF/DNS-rebinding controls if URLs are fetched, licensing metadata, pinned normalization, surfaced unstructured fallbacks, and maker-checker authorization.

## Common points

All agents support immutable versions, explicit lifecycle boundaries, provider-neutral interfaces, reproducible hashes/metadata, shared Persian normalization, and a publication gate that prevents partially processed content from becoming public. They consistently identify source-ID alignment, OCR/BiDi determinism, idempotent retries, typed-block handling, rollback semantics, and asynchronous processing as essential.

## Conflicts and reconciliation

The reviews differ mainly on optional extensions. Gemini prioritizes richer evaluation metrics; Qwen prioritizes embedding routing and migration sequencing; GLM favors extensible block registries and outbox-driven lifecycle operations; Claude requires the most explicit security and authorization clauses. These are complementary. The contract keeps the approved state names and publication gate, while adding their compatible constraints as normative requirements or explicitly deferred implementation details.

## Codex validation

The current repository tests for retrieval evaluation/dataset/benchmark pass (`12 passed`). No production schema, migration, ingestion execution, or PGVector benchmark was changed. Staging PostgreSQL remains blocked by the existing credential mismatch, so database-backed behavior is unvalidated. Existing code still has mutable ingestion and incomplete provenance; this specification addresses those as future contract obligations rather than claiming they are implemented.

## Commander decision required

Approve or reject this formal contract specification. If approved, authorize a separate implementation plan/review for additive models, migration/backfill, retrieval pointer routing, and contract tests. No implementation has been performed from agent advice alone.
