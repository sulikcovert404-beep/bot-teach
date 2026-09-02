import pytest

from app.services.rag import (
    Citation,
    CitationManifest,
    GroundingState,
    RetrievalRequest,
    RetrievedChunk,
    SourceChunk,
    SourceGuardian,
)


def test_retrieval_request_validates_contract_limits() -> None:
    assert RetrievalRequest("فتوسنتز", limit=20, scope="school-1").scope == "school-1"
    with pytest.raises(ValueError, match="query"):
        RetrievalRequest(" ")
    with pytest.raises(ValueError, match="between"):
        RetrievalRequest("query", limit=21)
    with pytest.raises(ValueError, match="scope"):
        RetrievalRequest("query", scope=" ")


def test_citation_manifest_deduplicates_and_validates_membership() -> None:
    first = RetrievedChunk(SourceChunk("الف", "book", page=2, chunk_id=7), score=0.8)
    duplicate = RetrievedChunk(SourceChunk("الف", "book", page=2, chunk_id=7), score=0.7)
    manifest = CitationManifest.from_chunks((first, duplicate))
    assert len(manifest.citations) == 1
    assert manifest.contains(Citation("book", chunk_id=7, page=2))
    assert not manifest.contains(Citation("other", chunk_id=7, page=2))


@pytest.mark.asyncio
async def test_source_guardian_returns_explicit_no_source_state() -> None:
    class EmptyRetriever:
        async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]:
            return []

    context = await SourceGuardian(EmptyRetriever()).retrieve_context(
        RetrievalRequest("پرسش")
    )
    assert context.state is GroundingState.NO_SOURCE
    assert context.citations == ()


@pytest.mark.asyncio
async def test_source_guardian_maps_legacy_retriever_to_contract() -> None:
    class Retriever:
        async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]:
            return [SourceChunk("پاسخ", "book", page=3, chunk_id=4, score=0.9)]

    context = await SourceGuardian(Retriever()).retrieve_context(
        RetrievalRequest("پرسش")
    )
    assert context.state is GroundingState.SUFFICIENT_EVIDENCE
    assert context.citations == (Citation("book", chunk_id=4, page=3),)
