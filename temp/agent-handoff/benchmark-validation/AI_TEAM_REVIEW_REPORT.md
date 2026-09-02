# AI TEAM REVIEW REPORT — PGVector Benchmark

**Scope:** advisory review of the sanitized handoff in `temp/agent-handoff/pgvector-benchmark-review/`. No implementation changes were made.

## Agent responses

### Gemini — architecture and evaluation strategy
- **Strengths:** provider-neutral runner, standard IR metrics, and explicit staging limitations.
- **Risks:** Persian normalization drift, cache/index configuration bias, and synthetic-set overfitting.
- **Missing:** index parameter sweeps, exact-vs-approximate baseline, filtered-search slices, negative/no-source cases, and generation faithfulness.
- **Recommendations:** deterministic normalization, warm/cold and interleaved runs, index recall/latency curves, stratified intent slices, and separate retrieval/generation tracks.

### Claude — critical review and hidden risks
- **Strengths:** clean retriever contract, deduplication, synthetic-data caveat, and honest staging limitations.
- **Risks:** report claims are not traceable to a reviewable pgvector harness/raw output; citation fallback ambiguity; conflict detection is not computed; four cases have no statistical power; expected-answer leakage surface.
- **Missing:** pgvector adapter/test, embedding model/version, per-case raw output, filter mismatch tests, warm/cold methodology, provenance header, and sample-size guard.
- **Recommendation:** do not accept quantitative pgvector claims until execution artifacts are attached and reproducible.

### Qwen — independent implementation review
- **Strengths:** provider-neutral protocols, deduplicated metrics, rollback/cleanup evidence, and transparent limitations.
- **Risks:** latency and metadata-filter enforcement are not guaranteed; score conversion is cosine-specific; ZWNJ handling is incomplete.
- **Missing:** EXPLAIN/index gate, percentile aggregation, filter-violation metric, faithfulness scoring, score-normalization contract, and warm/cold split.
- **Recommendations:** instrument the runner, add negative filter cases, validate index plans, expand Persian normalization, and standardize provider scores.

### GLM — alternative design review
- **Strengths:** isolated execution evidence, deterministic lexical baseline, and provider-neutral shape.
- **Risks:** one-query/five-run results are statistically insignificant; no index comparison; undisclosed embedding model; filters may be discarded; synthetic-only data.
- **Missing:** all-case/paraphrase execution, real curriculum corpus, aggregate metrics, hybrid RRF path, conflict/citation/faithfulness scoring, confidence intervals, concurrency, and injection/scope tests.
- **Recommendations:** expand corpus and trials, split warm/cold runs, record EXPLAIN/environment metadata, and compare lexical/vector/hybrid fairly with identical normalization.

## Common points

1. The abstraction boundary is sound, but current evidence is a smoke/contract benchmark, not a production gate.
2. Retrieval must be separated from citation correctness, faithfulness, abstention, and conflict resolution.
3. Versioned datasets, canonical source identifiers, graded/multi-source relevance, and stratified reporting are required.
4. Persian risks include ZWNJ, script variants, numerals, OCR, colloquial phrasing, formulas/tables, and curriculum drift.
5. Reproducibility requires pinned corpus/index/embedding versions, raw per-case output, latency instrumentation, warm/cold methodology, and confidence intervals.

## Conflicts

Gemini, Qwen, and GLM treated the Docker-local vector numbers as controlled evidence. Claude identified that the supplied code/handoff lacks a traceable pgvector harness or raw output and therefore treats those claims as unverified. Codex validation agrees with Claude's provenance concern. Agents also differed on some current implementation details; those must be rechecked before any change.

## Codex validation

- The sanitized handoff and Raw URLs were prepared and secret-scanned; no keys, tokens, passwords, credentials, or private data were found.
- `ENVIRONMENT_READINESS_UPDATE.md` states staging PostgreSQL was unreachable.
- `PGVECTOR_BENCHMARK_REPORT.md` claims a Docker-local run but supplies no harness, seed script, embedding model/version, or per-case raw output in the handoff; quantitative claims are therefore non-reproducible until attached.
- The report documents synthetic data, five runs, no warm/cold split, and unmeasured filter mismatch.

## Recommended next actions

1. Do not use current numbers as a release or provider-selection gate; reconcile provenance first.
2. Attach a reproducible harness, seed/embedding metadata, commit and dataset hashes, EXPLAIN output, and raw per-case results.
3. Expand and stratify the Persian dataset with paraphrase, ZWNJ/numeral/OCR, multi-hop, no-source, conflict, wrong-grade/subject, and adversarial cases.
4. Separate retrieval, citation, faithfulness, abstention, and conflict metrics; propagate graded relevance and report per-slice confidence intervals.
5. Add lexical, vector, hybrid/RRF, exact/approximate, filter-on/off, and warm/cold comparisons with latency percentiles.

**Commander decision required:** approve this validation and dataset-expansion plan, request changes, or authorize a scoped implementation task. No code change is authorized by this review alone.
