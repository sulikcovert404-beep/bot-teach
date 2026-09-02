# BENCHMARK VALIDATION UPGRADE REPORT

## Files changed

- `app/services/retrieval_benchmark.py`: captures deterministic raw evidence for every case and exposes `BenchmarkResult.to_report()`.
- `data/rag_eval_v1.json`: promoted to synthetic Dataset V1.1 with eight cases.
- `tests/test_retrieval_benchmark.py`: verifies raw per-case output.
- `tests/test_retrieval_dataset.py`: verifies V1.1 coverage and Persian edge-case fixtures.

## Dataset coverage

The synthetic fixture contains exact, related, no-source, conflict, multi-hop, Persian numeral, ZWNJ, OCR-like, and adversarial out-of-corpus cases. It remains explicitly synthetic and is not a production corpus.

## Output format

Each provider result now includes `raw_cases`. Every record stores query ID and text, retriever name, ordered source IDs, rank, scores, requested filters, measured latency, expected sources, and the computed metric object. `to_report()` adds aggregate recall, precision, MRR, and nDCG while retaining per-case evaluations.

## Validation

`python -m pytest tests/test_retrieval_benchmark.py tests/test_retrieval_dataset.py tests/test_retrieval_evaluation.py -q` → **12 passed**.

## Limitations

- The data is synthetic; it cannot establish production retrieval quality.
- Real PGVector execution remains blocked by staging PostgreSQL readiness.
- Citation, faithfulness, index-plan, warm/cold, and confidence-interval reporting remain separate follow-up work.

## Next recommendation

After Commander review, attach run identifiers and persist `to_report()` JSON for each benchmark run. Then expand with approved real curriculum data and execute only after PostgreSQL readiness evidence is available.
