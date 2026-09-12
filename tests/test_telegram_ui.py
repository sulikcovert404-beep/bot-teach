from app.services.telegram_ui import (
    NavigationKeyboard,
    SchoolAdminKeyboard,
    StudentKeyboard,
    TeacherKeyboard,
    content_card,
    empty_state,
    error_message,
    lesson_card,
    progress_card,
)


def test_role_keyboards_expose_only_role_menu() -> None:
    assert len(StudentKeyboard.build()["keyboard"]) == 6
    assert len(TeacherKeyboard.build()["keyboard"]) == 5
    assert len(SchoolAdminKeyboard.build()["keyboard"]) == 5
    assert NavigationKeyboard.build("TEACHER") == TeacherKeyboard.build()


def test_component_messages_have_actionable_contracts() -> None:
    lesson = lesson_card("فیزیک", grade="دهم", estimated_minutes=20)
    assert lesson.kind == "lesson_card"
    assert lesson.primary_action == "شروع درس"
    assert "پایه: دهم" in lesson.text
    assert error_message().primary_action == "تلاش دوباره"
    assert empty_state().fallback_action == "/menu"
    assert progress_card(None).primary_action is None
    assert content_card("تمرین").text.startswith("📘")
