from app.services.ai_gateway import AIProvider, AIRequest, AIResponse, ModelRouter


class TeacherAssistant:
    def __init__(self, provider: AIProvider, router: ModelRouter) -> None:
        self._provider = provider
        self._router = router

    async def create_lesson_plan(
        self, topic: str, *, grade: str, minutes: int = 45, max_tokens: int = 1600
    ) -> AIResponse:
        if not topic.strip() or not grade.strip() or not 10 <= minutes <= 240:
            raise ValueError("Lesson plan parameters are invalid")
        request = AIRequest(
            prompt=(
                f"برای پایه {grade} درباره‌ی موضوع «{topic}» یک طرح درس فارسی {minutes} دقیقه‌ای "
                "با هدف یادگیری، مراحل تدریس، فعالیت کلاسی و ارزشیابی بنویس."
            ),
            max_tokens=max_tokens,
            task_type="teacher_assistant",
        )
        return await self._provider.generate(self._router.route(request))
