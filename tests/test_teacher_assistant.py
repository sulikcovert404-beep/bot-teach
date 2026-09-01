import pytest

from app.services.ai_gateway import AIResponse, ModelRouter
from app.services.teacher_assistant import TeacherAssistant


class FakeProvider:
    def __init__(self) -> None:
        self.request = None

    async def generate(self, request):
        self.request = request
        return AIResponse(text="طرح درس", model=request.model or "unknown")


@pytest.mark.asyncio
async def test_teacher_assistant_creates_lesson_plan() -> None:
    provider = FakeProvider()
    result = await TeacherAssistant(provider, ModelRouter("test-model")).create_lesson_plan(
        "کسرها", grade="هفتم"
    )
    assert result.text == "طرح درس"
    assert provider.request.task_type == "teacher_assistant"


@pytest.mark.asyncio
async def test_teacher_assistant_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        await TeacherAssistant(FakeProvider(), ModelRouter("test-model")).create_lesson_plan(
            "", grade="هفتم"
        )
