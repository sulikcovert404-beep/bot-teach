# PGVECTOR BENCHMARK REPORT (sanitized handoff)

Environment: Docker-local isolated pgvector benchmark completed; staging connectivity remains blocked.
Metrics: lexical and PgVectorStore compared using Recall@2, Precision@2, MRR, Citation Accuracy, P50/P95.
Latency: query-to-result only; seed/cleanup excluded; five runs; warm/cold split not performed.
Filter: grade/subject filter path exercised; mismatch behavior not independently measured.
Limitations: synthetic small fixture; no production acceptance claim; Persian ZWNJ/OCR variants absent.
