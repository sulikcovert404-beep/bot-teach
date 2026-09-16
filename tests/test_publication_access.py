from app.services.publication_access import PublicationContext, can_access, can_publish


def test_publish_requires_owner_and_same_tenant() -> None:
    assert can_publish(PublicationContext(1, 1, "a", "a"))
    assert not can_publish(PublicationContext(2, 1, "b", "a"))
    assert not can_publish(PublicationContext(1, 2, "a", "a"))

def test_access_requires_membership_entitlement_and_publication() -> None:
    assert can_access(is_member=True, has_entitlement=True, published=True)
    assert not can_access(is_member=False, has_entitlement=True, published=True)
    assert not can_access(is_member=True, has_entitlement=False, published=True)
    assert not can_access(is_member=True, has_entitlement=True, published=False)
