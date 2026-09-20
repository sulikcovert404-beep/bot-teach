"""Provider-neutral, side-effect-free knowledge ingestion contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.services.persian_text import normalize_persian_text


class ReviewState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VectorAction(StrEnum):
    INDEX = "INDEX"
    REVOKE = "REVOKE"
    REBUILD = "REBUILD"
    NOOP = "NOOP"


@dataclass(frozen=True)
class OcrBlock:
    text: str
    page: int
    column: int = 0
    top: float = 0.0
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.page < 1 or self.column < 0 or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Invalid OCR block metadata")


def order_ocr_blocks(blocks: list[OcrBlock], *, rtl: bool = True) -> list[OcrBlock]:
    """Order blocks by page, then column, then vertical position.

    Persian layouts read right-to-left by default; ties retain input order.
    """
    direction = -1 if rtl else 1
    ordered = sorted(
        enumerate(blocks),
        key=lambda pair: (pair[1].page, direction * pair[1].column, pair[1].top, pair[0]),
    )
    return [item for _, item in ordered]


@dataclass(frozen=True)
class AssessmentUnit:
    question: str
    options: tuple[str, ...] = ()
    answer: str | None = None
    explanation: str | None = None

    def as_atomic_text(self) -> str:
        parts = [self.question.strip()]
        if self.options:
            parts.append("گزینه‌ها: " + " | ".join(option.strip() for option in self.options))
        if self.answer:
            parts.append("پاسخ: " + self.answer.strip())
        if self.explanation:
            parts.append("توضیح: " + self.explanation.strip())
        return normalize_persian_text("\n".join(parts))


_MATH_BLOCK = re.compile(r"(?P<delim>\$\$|\\\[|\\\(|\$)(?P<body>.*?)(?P=delim)", re.DOTALL)


def isolate_math(text: str) -> tuple[tuple[str, str], ...]:
    """Split text into typed normal/math segments while preserving delimiters."""
    segments: list[tuple[str, str]] = []
    cursor = 0
    for match in _MATH_BLOCK.finditer(text):
        if match.start() > cursor:
            segments.append(("text", text[cursor : match.start()]))
        segments.append(("math", match.group(0)))
        cursor = match.end()
    if cursor < len(text):
        segments.append(("text", text[cursor:]))
    return tuple(segments)


@dataclass(frozen=True)
class ReviewItem:
    item_id: str
    text: str
    source_id: str
    page: int | None = None
    state: ReviewState = ReviewState.PENDING

    def approve(self) -> ReviewItem:
        return ReviewItem(self.item_id, self.text, self.source_id, self.page, ReviewState.APPROVED)

    def reject(self) -> ReviewItem:
        return ReviewItem(self.item_id, self.text, self.source_id, self.page, ReviewState.REJECTED)


def vector_action(*, review_state: ReviewState, indexed_digest: str | None, current_digest: str) -> VectorAction:
    if not current_digest.strip():
        raise ValueError("Current digest is required")
    if review_state is ReviewState.REJECTED:
        return VectorAction.REVOKE
    if review_state is not ReviewState.APPROVED:
        return VectorAction.NOOP
    if indexed_digest is None:
        return VectorAction.INDEX
    return VectorAction.NOOP if indexed_digest == current_digest else VectorAction.REBUILD
