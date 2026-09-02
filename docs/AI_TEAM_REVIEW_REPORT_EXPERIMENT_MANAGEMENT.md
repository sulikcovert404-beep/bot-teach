# AI TEAM REVIEW REPORT — RAG Experiment Management Design

**Status:** Review collected before design implementation. No experiment-management code changes were made.

## Agent responses

### Gemini — experiment tracking architecture

Recommended a provider-neutral run registry keyed by dataset, retriever, embedding and environment versions; immutable run artifacts; stratified comparisons; and separate retrieval, Source Guardian, and generation tracks. Risks include Persian normalization drift, test-set contamination, chunk-ID coupling, and missing Pareto/latency reporting. Suggested warm-up/interleaving, canonical curriculum coordinates, R-Precision/MAP, and rejection matrices.

### Claude — critical reliability review

Flagged a provenance risk: artifacts accept caller-supplied version labels without verifying them against the cases/configuration that produced the result. It also identified raw question/score retention as a possible privacy and access-control concern, memory growth from retaining all raw cases, and the need for immutable hashes, schema validation, retention rules, and leakage guards. The initial handoff omission of `rag_eval_v1.json` was corrected before this report.

### Qwen — implementation and scalability review

Confirmed the portable envelope and raw evidence shape, while recommending streaming JSONL/Parquet for large datasets, an artifact comparison/regression API, strict execution metadata, filter-violation metrics, UUID/ULID run IDs, and concurrency/warm-cold measurements. It also repeated the Persian tokenization bias risk from naive whitespace splitting.

### GLM — alternative design review

The requested run returned a provider capacity error (`Model is currently at capacity`); no design advice was received. It remains an external availability blocker and must not be treated as approval or evidence.

## Common points

1. Keep experiment management outside the provider-neutral retrieval contract.
2. Treat artifacts as immutable, versioned evidence with reproducible metadata and raw per-case traceability.
3. Add comparison and regression views across dataset, retriever, embedding, environment, and metric slices.
4. Protect Persian evaluation validity through shared normalization, curriculum-version fields, stratification, and adversarial cases.
5. Plan for large runs with streaming/retention controls instead of unbounded in-memory raw output.

## Conflicts

- Gemini emphasized analytical slices and metric methodology; Qwen emphasized streaming and API mechanics.
- Claude questioned caller-supplied metadata integrity and privacy boundaries more strongly than the other reviews.
- GLM provided no response because of provider capacity; no conflict can be resolved for that role.

## Codex validation

- Handoff is sanitized and contains no credentials, tokens, or private user data.
- Handoff now includes `rag_eval_v1.json`; all Raw URLs checked during preparation returned HTTP 200.
- Current artifact implementation is an in-memory, JSON-serializable envelope. It does not yet persist externally, compare runs, enforce metadata hashes, or stream large outputs.
- No implementation change is authorized by this review alone.

## Commander decision required

Approve a scoped experiment-management design, request revisions, or defer until GLM can provide an alternative review. If approved, the first implementation slice should define immutable metadata/hash validation and a small comparison API while retaining provider neutrality and avoiding PGVector or retrieval changes.
