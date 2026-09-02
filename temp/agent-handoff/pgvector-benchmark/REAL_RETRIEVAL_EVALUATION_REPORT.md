# Real Retrieval Evaluation Report

The controlled benchmark runner was executed against a synthetic Persian SourceChunk fixture using the provider-neutral RetrieverFn contract. The lexical baseline retrieved the expected exact source for the first case and emitted Recall@K, deduplicated Precision@K, MRR, nDCG@K, R-Precision, citation match, source coverage, no-source and conflict fields.

PgVectorStore remains injectable through the same runner. No active PostgreSQL staging connection was available during this run, so no vector metrics or latency values were fabricated. Full pytest (134 tests at the time of the controlled run), Ruff and Mypy passed. This report contains no credentials, private data, production thresholds, index tuning, reranker, ingestion, or embedding-model changes.
