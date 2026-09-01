from dataclasses import dataclass

from app.services.ai_gateway import AIProvider, AIRequest, AIResponse, ModelRouter


@dataclass(frozen=True)
class EducationalAI:
    provider: AIProvider
    router: ModelRouter

    async def summarize(self, text: str, *, max_tokens: int = 800) -> AIResponse:
        if not text.strip():
            raise ValueError("Text is required")
        request = AIRequest(
            prompt=("متن آموزشی زیر را به فارسی، دقیق و ساختاریافته خلاصه کن و نکات کلیدی را جدا کن:\n\n" + text),
            max_tokens=max_tokens,
            task_type="smart_summary",
        )
        return await self.provider.generate(self.router.route(request))

    async def generate_questions(self, text: str, *, count: int = 5, max_tokens: int = 1200) -> AIResponse:
        if not text.strip() or not 1 <= count <= 20:
            raise ValueError("Text and question count are invalid")
        request = AIRequest(
            prompt=(
                f"از متن آموزشی زیر {count} سؤال چهارگزینه‌ای فارسی تولید کن. "
                "برای هر سؤال پاسخ صحیح و توضیح کوتاه ارائه بده:\n\n" + text
            ),
            max_tokens=max_tokens,
            task_type="question_generator",
        )
        return await self.provider.generate(self.router.route(request))

    async def generate_exam(self, text: str, *, count: int = 10, max_tokens: int = 2400) -> AIResponse:
        if not text.strip() or not 1 <= count <= 50:
            raise ValueError("Text and exam question count are invalid")
        request = AIRequest(
            prompt=(
                f"برای متن آموزشی زیر یک آزمون فارسی با {count} سؤال تولید کن. "
                "سؤال‌ها، گزینه‌ها، پاسخ‌نامه و بارم هر سؤال را مشخص کن:\n\n" + text
            ),
            max_tokens=max_tokens,
            task_type="exam_generator",
        )
        return await self.provider.generate(self.router.route(request))

    async def correct_exam(self, answer_key: str, answers: str, *, max_tokens: int = 1200) -> AIResponse:
        if not answer_key.strip() or not answers.strip():
            raise ValueError("Answer key and answers are required")
        request = AIRequest(
            prompt=(
                "پاسخ‌های دانش‌آموز را با کلید زیر تصحیح کن، نمره و توضیح خطاها را به فارسی بده.\n"
                f"کلید پاسخ:\n{answer_key}\nپاسخ دانش‌آموز:\n{answers}"
            ),
            max_tokens=max_tokens,
            task_type="exam_corrector",
        )
        return await self.provider.generate(self.router.route(request))
