from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SourceChunk:
    text: str
    source_id: str
    page: int | None = None


class Retriever(Protocol):
    async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]: ...


class SourceGuardian:
    """Ensures source-grounded features can distinguish cited context from general knowledge."""

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    async def context_for(self, query: str) -> list[SourceChunk]:
        return await self._retriever.retrieve(query)

    async def grounded_prompt(self, query: str) -> str:
        chunks = await self.context_for(query)
        if not chunks:
            return (
                "به منبع آموزشی معتبر دسترسی پیدا نشد. پاسخ قطعی نساز و فقط اعلام کن که "
                "برای پاسخ مستند، منبع لازم است."
            )
        context = "\n\n".join(
            f"[منبع: {chunk.source_id}{f'، صفحه {chunk.page}' if chunk.page else ''}]\n{chunk.text}"
            for chunk in chunks
        )
        return (
            "فقط بر اساس منابع زیر پاسخ بده. اگر پاسخ در منابع نیست، صریحاً بگو اطلاعات کافی "
            "وجود ندارد و شناسه منبع مرتبط را ذکر کن.\n\n"
            f"منابع:\n{context}\n\nپرسش:\n{query}"
        )
