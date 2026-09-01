import pytest

from app.services.ai_gateway import AIResponse, ModelRouter
from app.services.ai_tutor import AITutor
from app.services.rag import SourceChunk


class FakeProvider:
    def __init__(self) -> None:
        self.request = None

    async def generate(self, request):
        self.request = request
        return AIResponse(text="پاسخ مستند", model="fake")


class FakeRetriever:
    async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]:
        return [SourceChunk(text="سلول واحد بنیادی زندگی است.", source_id="book-1", page=2)]


@pytest.mark.asyncio
async def test_tutor_includes_citation_context() -> None:
    provider = FakeProvider()
    result = await AITutor(provider, ModelRouter("fake"), FakeRetriever()).answer("سلول چیست؟")
    assert result.text == "پاسخ مستند"
    assert "book-1" in provider.request.prompt
    assert provider.request.task_type == "ai_tutor"
