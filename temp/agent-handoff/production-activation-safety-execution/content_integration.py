"""Small provider-neutral integration boundary for content persistence and auth."""
from dataclasses import dataclass, replace
from typing import Any

from .admin_authorization import Actor, AuthorizationContext, authorize
from .content import ContentDraft, ContentResult, validate_content
from .content_commands import CreateContentVersionCommand, UpdateContentMetadataCommand


@dataclass(frozen=True)
class PersistedContent:
    content_id: int
    creator_id: str
    draft: ContentDraft
    metadata: dict[str, Any]
    version: int = 1


class ContentRepository:
    """In-memory adapter used by the integration boundary; no external I/O."""

    def __init__(self) -> None:
        self._items: dict[int, PersistedContent] = {}
        self._next_id = 1

    def create(self, creator_id: str, draft: ContentDraft, metadata: dict[str, Any]) -> PersistedContent:
        item = PersistedContent(self._next_id, creator_id, draft, dict(metadata))
        self._items[item.content_id] = item
        self._next_id += 1
        return item

    def get(self, content_id: int) -> PersistedContent | None:
        return self._items.get(content_id)

    def list_for_creator(self, creator_id: str) -> tuple[PersistedContent, ...]:
        """Return a stable, read-only snapshot ordered by content id."""
        return tuple(self._items[key] for key in sorted(self._items) if self._items[key].creator_id == creator_id)

    def update_metadata(self, content_id: int, metadata: dict[str, Any], expected_version: int) -> PersistedContent:
        current = self._items[content_id]
        if current.version != expected_version:
            raise ValueError("content version conflict")
        updated = replace(current, metadata=dict(metadata), version=current.version + 1)
        self._items[content_id] = updated
        return updated


class ContentIntegrationService:
    def __init__(self, repository: ContentRepository | None = None) -> None:
        self.repository = repository or ContentRepository()

    def create(self, command: CreateContentVersionCommand, actor: Actor, draft: ContentDraft, metadata: dict[str, Any]) -> PersistedContent:
        decision = authorize(command, actor, AuthorizationContext(creator_id=actor.actor_id))
        if not decision.allowed:
            raise PermissionError(decision.reason_code)
        result: ContentResult = validate_content(draft)
        if result.state.value != "ACCEPTED":
            raise ValueError(result.reason)
        return self.repository.create(actor.actor_id, draft, metadata)

    def update_metadata(self, command: UpdateContentMetadataCommand, actor: Actor) -> PersistedContent:
        current = self.repository.get(command.content_version_id)
        if current is None:
            raise KeyError(command.content_version_id)
        decision = authorize(command, actor, AuthorizationContext(creator_id=current.creator_id))
        if not decision.allowed:
            raise PermissionError(decision.reason_code)
        return self.repository.update_metadata(command.content_version_id, dict(command.metadata), command.expected_version)
