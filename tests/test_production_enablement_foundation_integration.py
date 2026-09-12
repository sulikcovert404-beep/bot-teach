import pytest

from app.services.admin_authorization import Actor, AuthorizationContext, PrincipalType, Role
from app.services.authorization_wiring import evaluate_content_access
from app.services.content import ContentDraft
from app.services.content_commands import CreateContentVersionCommand, UpdateContentMetadataCommand
from app.services.content_integration import ContentIntegrationService


def creator(actor_id="creator"):
    return Actor(actor_id, frozenset({Role.CREATOR}), PrincipalType.HUMAN)


def create_command(key="k"):
    return CreateContentVersionCommand(key, f"hash-{key}", 1, f"digest-{key}")


def test_create_authorize_then_persist_and_audit_match():
    service = ContentIntegrationService()
    actor = creator()
    command = create_command()
    audit = evaluate_content_access(command, actor, AuthorizationContext(creator_id=actor.actor_id))
    item = service.create(command, actor, ContentDraft("عنوان", "متن"), {"grade": 7})
    assert audit.allowed is True and audit.reason_code is None
    assert item.creator_id == actor.actor_id and service.repository.get(item.content_id) == item


def test_update_authorize_then_version_check():
    service = ContentIntegrationService()
    item = service.create(create_command(), creator(), ContentDraft("t", "b"), {})
    updated = service.update_metadata(
        UpdateContentMetadataCommand("u", "uh", item.content_id, {"grade": 8}, item.version), creator()
    )
    assert updated.version == item.version + 1
    with pytest.raises(ValueError, match="version conflict"):
        service.update_metadata(
            UpdateContentMetadataCommand("u2", "uh2", item.content_id, {"grade": 9}, item.version), creator()
        )


def test_denied_access_has_no_mutation():
    service = ContentIntegrationService()
    owner = creator()
    item = service.create(create_command(), owner, ContentDraft("t", "b"), {"grade": 7})
    before = service.repository.get(item.content_id)
    denied = evaluate_content_access(
        UpdateContentMetadataCommand("u", "uh", item.content_id, {"grade": 8}, item.version),
        creator("other"), AuthorizationContext(creator_id=owner.actor_id),
    )
    assert denied.allowed is False and denied.reason_code == "invalid_ownership"
    with pytest.raises(PermissionError, match="invalid_ownership"):
        service.update_metadata(
            UpdateContentMetadataCommand("u", "uh", item.content_id, {"grade": 8}, item.version),
            creator("other"),
        )
    assert service.repository.get(item.content_id) == before
