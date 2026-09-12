import pytest

from app.services.admin_authorization import Actor, PrincipalType, Role
from app.services.content import ContentDraft
from app.services.content_commands import CreateContentVersionCommand, UpdateContentMetadataCommand
from app.services.content_integration import ContentIntegrationService


def actor(role=Role.CREATOR, actor_id="creator"):
    return Actor(actor_id, frozenset({role}), PrincipalType.HUMAN)


def test_create_and_update_with_owner_authorization():
    service = ContentIntegrationService()
    item = service.create(CreateContentVersionCommand("k", "h", 1, "digest"), actor(), ContentDraft("درس", "متن"), {"grade": 7})
    assert item.content_id == 1
    updated = service.update_metadata(UpdateContentMetadataCommand("u", "uh", 1, {"grade": 8}, 1), actor())
    assert updated.metadata["grade"] == 8 and updated.version == 2


def test_rejects_wrong_owner_and_invalid_draft():
    service = ContentIntegrationService()
    with pytest.raises(ValueError):
        service.create(CreateContentVersionCommand("k", "h", 1, "digest"), actor(), ContentDraft("", "متن"), {})
    service.create(CreateContentVersionCommand("k", "h", 1, "digest"), actor(), ContentDraft("t", "b"), {})
    with pytest.raises(PermissionError):
        service.update_metadata(UpdateContentMetadataCommand("u", "uh", 1, {"x": 1}, 1), actor(actor_id="other"))


def test_version_conflict_is_explicit():
    service = ContentIntegrationService()
    service.create(CreateContentVersionCommand("k", "h", 1, "digest"), actor(), ContentDraft("t", "b"), {})
    with pytest.raises(ValueError, match="version conflict"):
        service.update_metadata(UpdateContentMetadataCommand("u", "uh", 1, {"x": 1}, 9), actor())


def test_persistence_snapshot_is_stable_and_owner_scoped():
    service = ContentIntegrationService()
    service.create(CreateContentVersionCommand("k1", "h1", 1, "d1"), actor(), ContentDraft("t1", "b1"), {})
    service.create(CreateContentVersionCommand("k2", "h2", 2, "d2"), actor(actor_id="other"), ContentDraft("t2", "b2"), {})
    snapshot = service.repository.list_for_creator("creator")
    assert tuple(item.content_id for item in snapshot) == (1,)
