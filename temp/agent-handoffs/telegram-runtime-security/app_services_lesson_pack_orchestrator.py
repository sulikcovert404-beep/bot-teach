"""Application orchestration for generating, reusing, and delivering lesson packs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import asyncio
import json
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.models import GeneratedAsset

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


class SqlAlchemyAssetStore:
    """Persistent adapter using the qualified GeneratedAsset identity index."""

    def __init__(self, session) -> None:
        self.session = session

    async def get(self, *, lesson_id: int, content_version: str, asset_type: str, stage: SchoolStage) -> LessonPack | None:
        del lesson_id, content_version  # DB identity is the immutable numeric version id.
        raise ValueError("use get_for_request so content_version_id is explicit")

    async def get_for_request(self, request: LessonPackRequest, *, asset_type: str = "PACK") -> LessonPack | None:
        if request.content_version_id is None:
            raise ValueError("content_version_id is required for SQL persistence")
        row = (await self.session.execute(select(GeneratedAsset).where(
            GeneratedAsset.content_version_id == request.content_version_id,
            GeneratedAsset.asset_type == asset_type,
            GeneratedAsset.school_stage == request.stage.value,
            GeneratedAsset.language == request.language,
            GeneratedAsset.profile_version == "lesson-pack-v1",
            GeneratedAsset.review_state == "APPROVED",
        ))).scalar_one_or_none()
        if row is None:
            return None
        data = json.loads(row.content_json)
        data["stage"] = SchoolStage(data["stage"])
        data["mcq"] = tuple(data.get("mcq", ()))
        data["descriptive"] = tuple(data.get("descriptive", ()))
        data["answers"] = tuple(data.get("answers", ()))
        return LessonPack(**data)

    async def put_for_request(self, request: LessonPackRequest, pack: LessonPack, *, job_id: int, asset_type: str = "PACK") -> LessonPack:
        if request.content_version_id is None:
            raise ValueError("content_version_id is required for SQL persistence")
        payload = json.dumps({"lesson_id": pack.lesson_id, "content_version": pack.content_version,
            "stage": pack.stage, "language": pack.language, "script": pack.script,
            "podcast_script": pack.podcast_script, "pdf_markdown": pack.pdf_markdown,
            "mcq": pack.mcq, "descriptive": pack.descriptive, "answers": pack.answers,
            "content_hash": pack.content_hash, "content_version_id": request.content_version_id}, ensure_ascii=False)
        row = GeneratedAsset(job_id=job_id, content_version_id=request.content_version_id,
            asset_type=asset_type, content_json=payload, content_hash=pack.content_hash,
            school_stage=request.stage.value, language=request.language, profile_version="lesson-pack-v1",
            review_state="APPROVED")
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError:
            # A concurrent producer may win the canonical identity race.  Its
            # transaction can still be committing when this loser rolls back,
            # so retry the read briefly before surfacing the conflict.
            await self.session.rollback()
            for _ in range(3):
                existing = await self.get_for_request(request, asset_type=asset_type)
                if existing is not None:
                    return existing
                await asyncio.sleep(0.05)
            raise
        return pack


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

    async def generate_or_reuse_persisted(self, request: LessonPackRequest, *, job_id: int) -> LessonPack:
        """Persisted path; caller supplies the existing generation job/trace id."""
        if not isinstance(self.store, SqlAlchemyAssetStore):
            return await self.generate_or_reuse(request)
        existing = await self.store.get_for_request(request)
        if existing is not None:
            return existing
        pack = self.generator.build_or_reuse(request)
        return await self.store.put_for_request(request, pack, job_id=job_id)

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

    async def delivery_assets_persisted(
        self, request: LessonPackRequest, *, review_state: str, job_id: int
    ) -> tuple[DeliveryAsset, ...]:
        """Deliver approved assets after resolving the real persistent adapter."""
        if review_state != "APPROVED":
            raise PermissionError("UNAPPROVED_ASSET")
        pack = await self.generate_or_reuse_persisted(request, job_id=job_id)
        caption = f"{request.title} | {request.stage} | {request.content_version}"
        return (
            DeliveryAsset("PODCAST", pack.podcast_script, caption),
            DeliveryAsset("PDF", pack.pdf_markdown, caption),
            DeliveryAsset("MCQ", str(pack.mcq), caption),
            DeliveryAsset("DESCRIPTIVE", str(pack.descriptive), caption),
        )
