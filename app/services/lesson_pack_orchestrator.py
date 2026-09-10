"""Application orchestration for generating, reusing, and delivering lesson packs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import asyncio

from app.services.lesson_pack import LessonPack, LessonPackRequest, LessonPackService, SchoolStage


class AssetStore(Protocol):
    async def get(self, *, lesson_id: int, content_version: str, asset_type: str, stage: SchoolStage) -> LessonPack | None: ...
    async def put(self, pack: LessonPack, *, asset_type: str) -> None: ...


class InMemoryAssetStore:
    """Disposable store used by staging qualification until a DB adapter is wired."""

    def __init__(self) -> None:
        self._items: dict[tuple[int, str, str, SchoolStage], LessonPack] = {}
        self._locks: dict[tuple[int, str, str, SchoolStage], asyncio.Lock] = {}

    def lock_for(self, key: tuple[int, str, str, SchoolStage]) -> asyncio.Lock:
        return self._locks.setdefault(key, asyncio.Lock())

    async def get(self, *, lesson_id: int, content_version: str, asset_type: str, stage: SchoolStage) -> LessonPack | None:
        return self._items.get((lesson_id, content_version, asset_type, stage))

    async def put(self, pack: LessonPack, *, asset_type: str) -> None:
        self._items.setdefault((pack.lesson_id, pack.content_version, asset_type, pack.stage), pack)


@dataclass(frozen=True, slots=True)
class DeliveryAsset:
    asset_type: str
    content: str
    caption: str


class LessonPackOrchestrator:
    ASSET_TYPES = ("PODCAST", "PDF", "MCQ", "DESCRIPTIVE")

    def __init__(self, *, generator: LessonPackService | None = None, store: AssetStore | None = None) -> None:
        self.generator = generator or LessonPackService()
        self.store = store

    @staticmethod
    def generation_parameters(request: LessonPackRequest) -> dict[str, object]:
        """Stable parameters for the existing ContentGenerationJob idempotency key."""
        return {
            "content_version": request.content_version,
            "language": request.language,
            "lesson_id": request.lesson_id,
            "school_stage": request.stage.value,
            "script_version": "lesson-pack-v1",
        }

    async def generate_or_reuse(self, request: LessonPackRequest) -> LessonPack:
        key = (request.lesson_id, request.content_version, "PACK", request.stage)
        if self.store is not None:
            lock = self.store.lock_for(key) if isinstance(self.store, InMemoryAssetStore) else None
            if lock is not None:
                async with lock:
                    existing = await self.store.get(lesson_id=request.lesson_id, content_version=request.content_version, asset_type="PACK", stage=request.stage)
                    if existing is not None:
                        return existing
                    pack = self.generator.build_or_reuse(request)
                    await self.store.put(pack, asset_type="PACK")
                    return pack
            existing = await self.store.get(lesson_id=request.lesson_id, content_version=request.content_version, asset_type="PACK", stage=request.stage)
            if existing is not None:
                return existing
        pack = self.generator.build_or_reuse(request)
        if self.store is not None:
            await self.store.put(pack, asset_type="PACK")
        return pack

    async def delivery_assets(self, request: LessonPackRequest, *, review_state: str) -> tuple[DeliveryAsset, ...]:
        if review_state != "APPROVED":
            raise PermissionError("UNAPPROVED_ASSET")
        pack = await self.generate_or_reuse(request)
        caption = f"{request.title} | {request.stage} | {request.content_version}"
        return (
            DeliveryAsset("PODCAST", pack.podcast_script, caption),
            DeliveryAsset("PDF", pack.pdf_markdown, caption),
            DeliveryAsset("MCQ", str(pack.mcq), caption),
            DeliveryAsset("DESCRIPTIVE", str(pack.descriptive), caption),
        )
