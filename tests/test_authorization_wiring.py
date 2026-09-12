from app.services.admin_authorization import Actor, AuthorizationContext, PrincipalType, Role
from app.services.authorization_wiring import evaluate_content_access
from app.services.content_commands import CreateContentVersionCommand


def test_authorization_decision_is_auditable_and_deterministic():
    command = CreateContentVersionCommand("k", "h", 1, "digest")
    actor = Actor("creator", frozenset({Role.CREATOR}), PrincipalType.HUMAN)
    first = evaluate_content_access(command, actor, AuthorizationContext(creator_id="creator"))
    second = evaluate_content_access(command, actor, AuthorizationContext(creator_id="creator"))
    assert first == second and first.allowed is True
    assert first.policy_version == "admin-auth-v1"


def test_wrong_owner_is_denied_with_reason():
    command = CreateContentVersionCommand("k", "h", 1, "digest")
    actor = Actor("other", frozenset({Role.CREATOR}), PrincipalType.HUMAN)
    record = evaluate_content_access(command, actor, AuthorizationContext(creator_id="owner"))
    assert record.allowed is False and record.reason_code == "invalid_ownership"
