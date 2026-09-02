"""Run a cleanup-safe lexical versus pgvector benchmark on isolated staging fixtures."""

import asyncio
import json
import os
from hashlib import sha256
from math import ceil
from time import perf_counter

from sqlalchemy import delete, select

from app.db.base import build_session_factory, dispose_session_factory
from app.db.models import SourceChunk as SourceChunkModel
from app.db.models import SourceDocument
from app.services.document_ingestion import DatabaseRetriever
from app.services.retrieval_evaluation import evaluate_ranked_sources
from app.services.vector_store import PgVectorStore, VectorSearchRequest

SOURCE_PREFIX = "controlled-pgvector-benchmark"
EMBEDDING_MODEL = "controlled-benchmark-fixture"
QUERY = "نیرو چیست"
EXPECTED_SOURCE = f"{SOURCE_PREFIX}-exact"


def vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second] + [0.0] * 766


def percentile(values: list[float], percentage: int) -> float:
    if not values or not 0 < percentage <= 100:
        raise ValueError("Percentile requires values and a percentage between 1 and 100")
    return sorted(values)[min(ceil(len(values) * percentage / 100) - 1, len(values) - 1)]


async def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    factory = build_session_factory(database_url)
    try:
        async with factory() as session:
            existing = select(SourceDocument.id).where(SourceDocument.source_id.like(f"{SOURCE_PREFIX}%"))
            await session.execute(delete(SourceChunkModel).where(SourceChunkModel.document_id.in_(existing)))
            await session.execute(delete(SourceDocument).where(SourceDocument.source_id.like(f"{SOURCE_PREFIX}%")))
            fixtures = [
                (EXPECTED_SOURCE, "نیرو چیست؟ نیرو برهم‌کنش میان اجسام است.", vector(1.0)),
                (f"{SOURCE_PREFIX}-related", "نیرو و حرکت در فیزیک بررسی می‌شوند.", vector(0.9, 0.1)),
                (f"{SOURCE_PREFIX}-noise", "فتوسنتز فرایند تولید غذا در گیاهان است.", vector(0.0, 1.0)),
            ]
            documents: list[SourceDocument] = []
            for source_id, text, _ in fixtures:
                document = SourceDocument(source_id=source_id, title="Controlled benchmark fixture")
                document.chunks.append(
                    SourceChunkModel(
                        chunk_index=0,
                        text=text,
                        page=1,
                        source_type="official_book",
                        grade="دهم",
                        subject="فیزیک",
                        content_hash=sha256(text.encode()).hexdigest(),
                    )
                )
                documents.append(document)
            session.add_all(documents)
            await session.flush()
            vector_store = PgVectorStore(session)
            for document, (_, _, embedding) in zip(documents, fixtures):
                await vector_store.upsert_embedding(
                    chunk_id=document.chunks[0].id,
                    embedding=embedding,
                    embedding_model=EMBEDDING_MODEL,
                )

            async def run_provider(provider: str) -> dict[str, object]:
                timings: list[float] = []
                ranked: list[str] = []
                for _ in range(5):
                    started = perf_counter()
                    if provider == "lexical":
                        found = await DatabaseRetriever(session).retrieve(QUERY, limit=2)
                    else:
                        found = await vector_store.search(
                            VectorSearchRequest(embedding=vector(1.0), limit=2, grade="دهم", subject="فیزیک")
                        )
                    timings.append((perf_counter() - started) * 1_000)
                    ranked = [chunk.source_id for chunk in found]
                evaluation = evaluate_ranked_sources(
                    query_id="controlled-near-exact",
                    expected_sources={EXPECTED_SOURCE},
                    ranked_sources=ranked,
                    k=2,
                    cited_sources=ranked,
                )
                return {
                    "provider": provider,
                    "ranked_sources": ranked,
                    "recall_at_2": evaluation.recall_at_k,
                    "precision_at_2": evaluation.precision_at_k,
                    "mrr": evaluation.reciprocal_rank,
                    "citation_accuracy": evaluation.citation_match,
                    "p50_latency_ms": percentile(timings, 50),
                    "p95_latency_ms": percentile(timings, 95),
                }

            report = {
                "dataset": "rag-eval-v1-synthetic / controlled staging fixture",
                "query": QUERY,
                "providers": [await run_provider("lexical"), await run_provider("vector")],
                "limitations": [
                    "Small synthetic fixture; results are not production acceptance evidence.",
                    "Hybrid retrieval, reranking, index tuning and thresholds are out of scope.",
                ],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            await session.rollback()
    finally:
        await dispose_session_factory(factory)


if __name__ == "__main__":
    asyncio.run(main())
