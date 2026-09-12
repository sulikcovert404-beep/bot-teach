import hashlib
import time
from dataclasses import dataclass, field

from app.services.ai_gateway import AIProvider, AIRequest, AIResponse, ModelRouter
from app.services.rag import RetrievalRequest, Retriever, SourceGuardian

_ANSWER_CACHE: dict[str, tuple[AIResponse, float]] = {}
_CACHE_TTL_SECONDS = 600.0  # 10 minutes cache for frequently asked curriculum questions


def _normalize_query(query: str) -> str:
    cleaned = "".join(ch for ch in query.strip().lower() if ch.isalnum() or ch.isspace())
    return " ".join(cleaned.split())


@dataclass(frozen=True)
class AITutor:
    provider: AIProvider
    router: ModelRouter
    retriever: Retriever

    async def answer(self, query: str, *, max_tokens: int = 1_200) -> AIResponse:
        if not query.strip() or not 1 <= max_tokens <= 4_000:
            raise ValueError("Tutor query and token limit are invalid")

        norm_key = hashlib.sha256(_normalize_query(query).encode("utf-8")).hexdigest()
        now = time.time()

        cached_entry = _ANSWER_CACHE.get(norm_key)
        if cached_entry:
            cached_resp, cached_time = cached_entry
            if now - cached_time < _CACHE_TTL_SECONDS:
                return cached_resp

        guardian = SourceGuardian(self.retriever)
        context = await guardian.retrieve_context(
            RetrievalRequest(query=query, limit=5, minimum_score=0.0)
        )
        prompt = guardian.prompt_for_chunks(query, [item.chunk for item in context.chunks])
        request = AIRequest(prompt=prompt, max_tokens=max_tokens, task_type="ai_tutor")
        response = await self.provider.generate(self.router.route(request))

        # Evidence is authoritative retrieval metadata, kept separate from
        # model text so a model cannot invent source references.
        response = AIResponse(
            text=response.text,
            model=response.model,
            usage_tokens=response.usage_tokens,
            citations=tuple(context.citations),
        )

        # Store in cache
        _ANSWER_CACHE[norm_key] = (response, now)
        return response
