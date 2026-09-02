# CURRICULUM PIPELINE CONTRACT SPECIFICATION

Status: Draft for AI Team review. This document defines provider-neutral contracts only. It authorizes no ingestion execution, schema migration, upload flow, or production change.

## 1. ProcessingState contract

A `ContentVersion` has exactly one processing state:
`UPLOADED`, `PROCESSING`, `EXTRACTED`, `CHUNKED`, `EMBEDDING`, `VECTOR_SYNCING`, `VECTOR_SYNCED`, `VALIDATED`, `FAILED`, or `QUARANTINED`.

Transitions are explicit, auditable, and idempotent. `FAILED` records retryable/terminal classification, attempt count, error code, and safe diagnostic reference. `QUARANTINED` excludes the version from retrieval and requires an explicit administrative resolution. Published content is never mutated in place.

## 2. ReviewState contract

A version has one independent editorial state: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, or `RETIRED`. Rejected and retired versions remain available to authorized administrators but are excluded from public retrieval. Publication requires `processing_state=VALIDATED`, `review_state=APPROVED`, and vector readiness.

Every review transition records actor, role, previous state, next state, reason, timestamp, and request/idempotency key. A maker-checker policy may prevent the submitting actor from approving their own version.

## 3. PublicationPointer contract

For each logical source and retrieval scope, one relational pointer identifies the active `ContentVersion`. A pointer flip uses compare-and-swap against the expected current version and commits atomically with its audit row and transactional outbox event. The pointer can be switched to a previously validated version for rollback or set null for unpublish/retire. Retrieval resolves the pointer before reading chunks and never reads a partial version.

## 4. VectorSync lifecycle

Vector readiness is tracked independently: `VECTOR_PENDING`, `VECTOR_SYNCING`, `VECTOR_SYNCED`, `VECTOR_FAILED`. A sync job is idempotent by content-version, chunk hash, embedding-model, and index-generation identity. Partial vectors remain shadow data and cannot be published. Retryable failures may resume; terminal failures quarantine the version. Rollback is allowed only when the target version has compatible, complete vectors for the requested embedding/index identity.

## 5. Provenance schema

Each chunk must carry stable source identity and: logical source id, content-version id, source-file id/hash, book/edition/grade/subject, chapter/section/lesson, page start/end when available, structural path, chunk index/type, extraction timestamp, parser/OCR configuration versions, pipeline version, normalization policy version, chunk hash, embedding model, and index generation. Missing fields required by a source type fail validation; raw extracted text is preserved separately from normalized text.

## 6. Hash and digest specification

- `source_file_hash`: SHA-256 over canonical source bytes.
- `extracted_content_hash`: SHA-256 over canonical extracted block sequence.
- `chunk_content_hash`: SHA-256 over canonical normalized chunk payload plus structural path.
- `pipeline_digest`: canonical SHA-256 over source hash, parser version, OCR configuration version, normalizer version, chunker version, and relevant extraction options.

Canonical serialization is deterministic (UTF-8, normalized field ordering, explicit null policy). Hash equality permits a safe idempotent no-op; any digest change creates a new immutable version.

## 7. Persian normalization version contract

A single provider-neutral, version-pinned policy is consumed by ingestion, lexical retrieval, vector preparation, evaluation, and citation matching. It specifies Unicode normalization, Arabic Yeh/Kaf mapping, Persian/Arabic/Latin digit policy, whitespace, ZWNJ, tatweel, diacritics, punctuation, and documented OCR substitutions. Raw text remains available for provenance. Each version has regression/property tests and an explicit fallback policy; changing policy changes the pipeline digest.

## 8. Parser/OCR security boundary

Parser and OCR workers execute in isolated, restricted environments with no network, no script execution, bounded CPU/memory/time/output, restricted filesystem, decompression-bomb protection, and deterministic engine/configuration versions. Uploads undergo size limits, magic-byte MIME verification, polyglot rejection, malware scanning, safe filename handling, tenant/role authorization, and audit logging without raw content or secrets. Future URL imports require HTTPS allowlisting, DNS/IP rebinding protection, redirect controls, and revalidation at fetch time.

## 9. Source ID alignment rules

The same canonical identity must flow through book, edition, chapter, page, chunk, embedding, citation, and benchmark gold data. Define a versioned format such as `book:edition:page:chunk`; reject or quarantine records that cannot map deterministically. Identity generation occurs before embedding and is immutable thereafter. Real PGVector benchmarking is prohibited until a contract test proves round-trip identity alignment.

## 10. Transactional outbox contract

A committed pointer or lifecycle transition emits an outbox row in the same transaction. Each event has event id, aggregate/version id, event type, schema version, payload hash, created timestamp, delivery attempts, and processing status. Consumers are idempotent; dispatch failure does not roll back the committed publication. No consumer may make an unvalidated version visible.

## Compatibility and constraints

The contracts map to existing `RetrievalRequest`, `RetrievedChunk`, `SourceGuardian`, and `VectorStore` abstractions. Provider and storage implementations remain outside this specification. No destructive migration, ingestion execution, upload UI, OCR production deployment, or PGVector optimization is included.
