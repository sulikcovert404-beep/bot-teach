# AI TEAM REVIEW REPORT — Benchmark Reproducibility Upgrade + Dataset V1.1

**Status:** Advisory review complete. No implementation or architecture changes made.

## Agent responses

### Gemini — Benchmark Architecture Review
- **Strengths:** provider-neutral runner, deterministic lexical baseline, explicit per-case/stratified evaluation direction.
- **Risks:** Persian normalization drift, cache/index bias, synthetic-set overfitting, and chunk-ID coupling.
- **Missing:** pinned corpus and embedding metadata, frozen train/validation/test splits, raw per-case artifacts, confidence intervals, index comparisons, and explicit abstention/conflict evaluation.
- **Recommendations:** deterministic preprocessing shared by lexical/vector paths; multi-stage retrieval/generation tracks; warm/cold and interleaved runs; stratify by intent, grade, subject, and Bloom level.

### Claude — Critical Reliability Review
- **Strengths:** retriever contract, deduplicated metrics, schema validation, and honest staging limitations.
- **Critical risks:** quantitative benchmark claims are not independently traceable without a harness/raw outputs; citation metric fallback can silently become recall; four synthetic cases have no statistical power; expected-answer and corpus leakage are possible.
- **Mitigations:** attach executable harness, seeds, model/index versions, raw outputs, provenance headers, sample-size gates, leakage checks, and separate retrieval/citation/faithfulness reporting.

### Qwen — Independent Implementation Review
- **Strengths:** strict dataset/version validation, useful edge-case tests, explicit no-source/conflict cases, and provider-neutral interfaces.
- **Risks:** filter enforcement is not measured, cosine-specific score conversion, naive Persian tokenization, and missing reproducibility artifacts.
- **Missing/recommended:** filter-violation rate, EXPLAIN/index-plan gate, warm/cold split, score-normalization contract, raw run artifacts, and Persian ZWNJ/space/numeral/OCR variants.

### GLM — Alternative Design Review
- **Strengths:** clear separation of current smoke evidence from production claims and a scalable direction for lexical/vector/hybrid comparison.
- **Risks:** one-query/five-run results are statistically weak; staging PostgreSQL authentication is blocked; no index comparison, disclosed embedding model, or real curriculum corpus.
- **Recommendations:** expand to at least 100 stratified real curriculum cases; pin versions and hashes; capture per-case JSON, EXPLAIN output, latency percentiles, confidence intervals; compare lexical, vector, hybrid/RRF, filter on/off, and warm/cold paths.

## Common points

1. The architecture boundary is sound, but the current evidence is a contract/smoke benchmark rather than a production gate.
2. Dataset V1.1 needs version-pinned provenance, graded or multi-source relevance, stratification, and substantially more cases.
3. Retrieval, citation correctness, faithfulness, abstention, and conflict handling must be reported as separate tracks.
4. Reproducibility requires a runnable harness, seed/corpus/embedding/index metadata, commit and dataset hashes, raw per-case output, and latency methodology.
5. Persian evaluation must cover ZWNJ, Arabic/Persian character variants, numerals, OCR noise, formulas/tables, colloquial paraphrases, and curriculum/version drift.

## Conflicts

- Gemini/Qwen/GLM accepted parts of the existing local smoke evidence as controlled validation; Claude treated quantitative claims as unverified because the handoff lacks a traceable harness and raw outputs. Codex validation agrees with the provenance concern.
- Some agents inferred implementation details from report text. Those details require local revalidation before design changes.

## Codex validation

- Handoff files were sanitized and secret-scanned; no API keys, tokens, passwords, credentials, or private data were found.
- All ten handoff Raw URLs returned HTTP 200.
- The environment update records blocked staging PostgreSQL authentication, so real PGVector benchmark execution remains blocked.
- Existing reports explicitly identify synthetic data, limited runs, absent warm/cold split, and unmeasured filter/index behavior. No benchmark result was fabricated.

## Recommended next actions

1. Keep the real PGVector benchmark blocked until the Commander resolves PostgreSQL credentials/environment readiness.
2. Before implementation, attach the reproducibility harness, seed script, embedding/index metadata, EXPLAIN output, raw per-case results, and hashes.
3. Design Dataset V1.1 around stratified real curriculum data (target ≥100 cases) with paraphrase, multi-hop, no-source, conflict, wrong-grade/subject, adversarial, and Persian-orthography slices.
4. Define separate retrieval, citation, faithfulness, abstention, conflict, filter-violation, and latency metrics with confidence intervals.
5. Compare lexical, vector, hybrid/RRF, exact/approximate, filter-on/off, and warm/cold configurations under one normalization contract.

**Commander decision required:** approve this validation/design plan, request revisions, or authorize a scoped implementation task. Agent advice alone authorizes no code changes.
