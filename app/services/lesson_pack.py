"""Provider-neutral lesson-pack contracts and deterministic generation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Mapping


class SchoolStage(StrEnum):
    ELEMENTARY = "ELEMENTARY"
    LOWER_SECONDARY = "LOWER_SECONDARY"
    UPPER_SECONDARY = "UPPER_SECONDARY"


@dataclass(frozen=True, slots=True)
class LessonProfile:
    stage: SchoolStage
    tone: str
    target_grade: str
    max_script_words: int


PROFILES: Mapping[SchoolStage, LessonProfile] = {
    SchoolStage.ELEMENTARY: LessonProfile(SchoolStage.ELEMENTARY, "warm, story-based, concrete", "1-6", 120),
    SchoolStage.LOWER_SECONDARY: LessonProfile(SchoolStage.LOWER_SECONDARY, "friendly, explanatory, scientific", "7-9", 180),
    SchoolStage.UPPER_SECONDARY: LessonProfile(SchoolStage.UPPER_SECONDARY, "precise, exam-focused, technical", "10-12", 240),
}


@dataclass(frozen=True, slots=True)
class LessonPackRequest:
    lesson_id: int
    content_version: str
    title: str
    source_text: str
    stage: SchoolStage
    language: str = "fa-IR"


@dataclass(frozen=True, slots=True)
class LessonPack:
    lesson_id: int
    content_version: str
    stage: SchoolStage
    language: str
    script: str
    podcast_script: str
    pdf_markdown: str
    mcq: tuple[dict[str, object], ...]
    descriptive: tuple[dict[str, str], ...]
    answers: tuple[dict[str, str], ...]
    content_hash: str


class LessonPackService:
    """Generate deterministic, provider-neutral packs for a reviewed source."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, str, SchoolStage, str], LessonPack] = {}

    def build(self, request: LessonPackRequest) -> LessonPack:
        profile = PROFILES[request.stage]
        excerpt = " ".join(request.source_text.split())[:1200]
        script = (
            f"{request.title}\n\n"
            f"سطح {profile.target_grade}: {profile.tone}.\n"
            f"موضوع را با این مثال بررسی کن: {excerpt}"
        )
        podcast = f"[Podcast {request.stage}] {script}"
        pdf = f"# {request.title}\n\n{script}\n\n## نکته کلیدی\nبازبینی منبع و یادداشت‌برداری."
        mcq = (
            {"question": f"کدام گزینه به درس «{request.title}» مربوط است؟", "options": ("الف", "ب", "ج", "د"), "answer": "الف"},
        )
        descriptive = ({"question": f"یک توضیح کوتاه درباره «{request.title}» بنویسید."},)
        answers = ({"question": descriptive[0]["question"], "answer": "پاسخ باید بر اساس متن منبع و با ذکر دلیل باشد."},)
        canonical = json.dumps({"lesson_id": request.lesson_id, "content_version": request.content_version, "language": request.language, "stage": request.stage.value, "script": script, "podcast": podcast, "pdf": pdf, "mcq": mcq, "descriptive": descriptive, "answers": answers}, ensure_ascii=False, sort_keys=True)
        return LessonPack(request.lesson_id, request.content_version, request.stage, request.language, script, podcast, pdf, mcq, descriptive, answers, sha256(canonical.encode()).hexdigest())

    def build_or_reuse(self, request: LessonPackRequest) -> LessonPack:
        """Return one generated pack per lesson/version/profile/language."""
        key = (request.lesson_id, request.content_version, request.stage, request.language)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        pack = self.build(request)
        self._cache[key] = pack
        return pack
