import pytest

from app.services.ai_gateway import AIResponse, ModelRouter
from app.services.educational_ai import EducationalAI
from app.services.rag import SourceChunk, SourceGuardian


class FakeProvider:
    def __init__(self) -> None:
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return AIResponse(text="ok", model=request.model or "unknown")


@pytest.mark.asyncio
async def test_educational_ai_preserves_task_types() -> None:
    provider = FakeProvider()
    service = EducationalAI(provider, ModelRouter("test-model"))
    await service.summarize("درس علوم")
    await service.generate_questions("درس ریاضی", count=3)
    await service.generate_exam("درس فارسی", count=4)
    await service.correct_exam("۱:الف", "۱:ب")
    assert [request.task_type for request in provider.requests] == [
        "smart_summary",
        "question_generator",
        "exam_generator",
        "exam_corrector",
    ]


@pytest.mark.asyncio
async def test_educational_ai_rejects_invalid_input() -> None:
    service = EducationalAI(FakeProvider(), ModelRouter("test-model"))
    with pytest.raises(ValueError):
        await service.summarize(" ")
    with pytest.raises(ValueError):
        await service.generate_questions("متن", count=21)
    with pytest.raises(ValueError):
        await service.generate_exam("متن", count=51)
    with pytest.raises(ValueError):
        await service.correct_exam("", "پاسخ")


@pytest.mark.asyncio
async def test_source_guardian_builds_cited_prompt() -> None:
    class Retriever:
        async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]:
            return [SourceChunk("تهران", "book-1", 12)]

    prompt = await SourceGuardian(Retriever()).grounded_prompt("پایتخت ایران چیست؟")
    assert "book-1" in prompt
    assert "صفحه 12" in prompt
