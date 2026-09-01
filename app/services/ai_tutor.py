from dataclasses import dataclass

from app.services.ai_gateway import AIProvider, AIRequest, AIResponse, ModelRouter
from app.services.rag import Retriever, SourceGuardian


@dataclass(frozen=True)
class AITutor:
    provider: AIProvider
    router: ModelRouter
    retriever: Retriever

    async def answer(self, query: str, *, max_tokens: int = 1_200) -> AIResponse:
        if not query.strip() or not 1 <= max_tokens <= 4_000:
            raise ValueError("Tutor query and token limit are invalid")
        prompt = await SourceGuardian(self.retriever).grounded_prompt(query)
        request = AIRequest(prompt=prompt, max_tokens=max_tokens, task_type="ai_tutor")
        return await self.provider.generate(self.router.route(request))
