"""Pure content capability for deterministic draft validation."""
from dataclasses import dataclass
from enum import Enum


class ContentState(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ContentDraft:
    title: str
    body: str
    language: str = "fa"


@dataclass(frozen=True)
class ContentResult:
    state: ContentState
    title: str
    body: str
    language: str
    reason: str = ""


def validate_content(draft: ContentDraft) -> ContentResult:
    """Validate a draft without persistence, provider calls, or side effects."""
    if not isinstance(draft, ContentDraft):
        raise TypeError("draft must be a ContentDraft")
    if not draft.title.strip():
        return ContentResult(ContentState.REJECTED, draft.title, draft.body, draft.language, "title_required")
    if not draft.body.strip():
        return ContentResult(ContentState.REJECTED, draft.title, draft.body, draft.language, "body_required")
    if draft.language not in {"fa", "en"}:
        return ContentResult(ContentState.REJECTED, draft.title, draft.body, draft.language, "unsupported_language")
    return ContentResult(ContentState.ACCEPTED, draft.title, draft.body, draft.language)
