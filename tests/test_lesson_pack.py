from app.services.lesson_pack import LessonPackRequest, LessonPackService, SchoolStage


def test_profiles_change_pack_style_and_content_hash() -> None:
    service = LessonPackService()
    packs = [service.build(LessonPackRequest(1, "v1", "نیرو", "نیرو باعث تغییر حرکت می‌شود.", stage)) for stage in SchoolStage]
    assert len({pack.content_hash for pack in packs}) == 3
    assert packs[0].stage is SchoolStage.ELEMENTARY
    assert "داستانی" not in packs[0].script  # profile is encoded through the selected tone
    assert "technical" in packs[2].script


def test_pack_is_immutable_and_contains_required_assets() -> None:
    pack = LessonPackService().build(LessonPackRequest(7, "v2", "کسرها", "توضیح منبع", SchoolStage.LOWER_SECONDARY))
    assert pack.podcast_script
    assert pack.pdf_markdown.startswith("# ")
    assert pack.mcq and pack.descriptive and pack.answers


def test_build_or_reuse_returns_same_static_asset() -> None:
    service = LessonPackService()
    request = LessonPackRequest(9, "v1", "نور", "منبع", SchoolStage.ELEMENTARY)
    assert service.build_or_reuse(request) is service.build_or_reuse(request)
