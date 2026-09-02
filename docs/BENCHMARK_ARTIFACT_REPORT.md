# BENCHMARK ARTIFACT REPORT

## Files changed

- `app/services/retrieval_benchmark.py`
- `tests/test_retrieval_benchmark.py`

## Schema

`BenchmarkRunArtifact` is a provider-neutral, JSON-serializable envelope containing:

- `run_id`
- `dataset_version`
- `retriever_version`
- UTC `timestamp`
- caller-supplied `execution_metadata`
- per-provider `metric_snapshot`
- complete provider reports, including raw per-case evidence

The run identity is generated with UUID4; caller-provided identifiers are not trusted. `artifact_hash` is a SHA-256 digest of the canonical artifact payload. `compare_artifacts()` returns metric deltas for shared providers and refuses comparison when dataset versions differ.

`persist_run_artifact()` creates the envelope without choosing a database, filesystem, or vendor-specific persistence layer. Callers can serialize `to_report()` to their approved artifact store.

## Validation

`python -m pytest tests/test_retrieval_benchmark.py tests/test_retrieval_dataset.py tests/test_retrieval_evaluation.py -q` → **12 passed**.

## Limitations

This change builds the artifact envelope but does not write external files or database rows automatically. Real PGVector execution remains blocked by staging PostgreSQL readiness, and no production threshold is introduced.

## Next recommendation

Commander may approve a narrow persistence adapter that writes these envelopes to a reviewed local artifact path after each controlled run, including environment and commit hashes.
