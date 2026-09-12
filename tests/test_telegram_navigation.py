import pytest

from app.services.telegram_navigation import (
    NavigationAction,
    NavigationConfig,
    NavigationIntent,
    allowed_callback,
    build_inline_keyboard,
    build_reply_keyboard,
    build_role_keyboard,
    build_start_inline_keyboard,
    fallback_text,
    lesson_card_text,
    role_menu_labels,
)


def test_reply_keyboard_is_deterministic_and_persian() -> None:
    payload = build_reply_keyboard()
    assert payload == build_reply_keyboard()
    assert payload["is_persistent"] is True
    assert "ورود به کلاس هوشمند" in str(payload)


def test_reply_keyboard_web_app_buttons_use_fixed_url() -> None:
    payload = build_reply_keyboard(web_app_url="https://codeshow.ir/mini-app")
    assert payload["keyboard"][0][0]["web_app"] == {"url": "https://codeshow.ir/mini-app"}


def test_inline_web_app_uses_fixed_https_url() -> None:
    config = NavigationConfig("https://codeshow.ir/mini-app")
    payload = build_inline_keyboard(config)
    assert payload["inline_keyboard"][0][0]["web_app"] == {"url": config.web_app_url}
    assert payload["inline_keyboard"][0][-1]["callback_data"] == "help"


@pytest.mark.parametrize("url", [
    "http://codeshow.ir/mini-app",
    "https://codeshow.ir/mini-app?x=1",
    "https://codeshow.ir/mini-app#view",
    "not-a-url",
])
def test_web_app_url_is_fixed_https(url: str) -> None:
    with pytest.raises(ValueError):
        NavigationConfig(url)


def test_unknown_callbacks_fail_closed() -> None:
    assert allowed_callback("open:tutor") is NavigationAction.OPEN_TUTOR
    assert allowed_callback("open:arbitrary") is None
    assert fallback_text("unknown")


def test_custom_intents_preserve_zwnj_and_callback_shape() -> None:
    intents = (NavigationIntent(NavigationAction.HELP, "راهنمای‌کامل"),)
    payload = build_reply_keyboard(intents)
    assert payload["keyboard"][0][0]["text"] == "راهنمای‌کامل"


def test_role_keyboard_is_presentation_only_and_deterministic() -> None:
    assert role_menu_labels("teacher") == role_menu_labels("TEACHER")
    payload = build_role_keyboard("TEACHER")
    labels = [row[0]["text"] for row in payload["keyboard"]]
    assert labels == ["🏠 خانه", "🏫 کلاس‌های من", "📥 صف بررسی", "📚 محتوا", "📊 پیشرفت"]


def test_lesson_card_omits_unavailable_optional_data() -> None:
    card = lesson_card_text(subject="فیزیک", grade=None, estimated_minutes=None)
    assert "موضوع: فیزیک" in card
    assert "پایه:" not in card
    assert "زمان پیشنهادی:" not in card


def test_start_inline_keyboard_uses_fixed_url() -> None:
    payload = build_start_inline_keyboard("https://demo-ai.codeshow.ir/mini-app/")
    assert payload["inline_keyboard"][0][0]["text"] == "🎓 ورود به پنل آموزشی"
    assert payload["inline_keyboard"][0][0]["web_app"]["url"] == "https://demo-ai.codeshow.ir/mini-app/"
