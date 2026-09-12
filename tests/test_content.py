from app.services.content import ContentDraft, ContentState, validate_content


def test_valid_content_is_accepted_and_deterministic():
    draft = ContentDraft("درس", "متن آموزشی")
    assert validate_content(draft) == validate_content(draft)
    assert validate_content(draft).state is ContentState.ACCEPTED


def test_invalid_content_returns_typed_reasons():
    assert validate_content(ContentDraft("", "body")).reason == "title_required"
    assert validate_content(ContentDraft("title", "")).reason == "body_required"
    assert validate_content(ContentDraft("title", "body", "ar")).reason == "unsupported_language"


def test_draft_and_result_are_immutable():
    draft = ContentDraft("t", "b")
    try:
        draft.title = "x"
        assert False
    except AttributeError:
        pass
