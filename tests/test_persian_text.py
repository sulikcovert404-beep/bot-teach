from app.services.persian_text import is_rtl_safe, normalize_persian_text


def test_normalization_unifies_arabic_glyphs_and_invisible_spacing() -> None:
    assert normalize_persian_text("مي\u200bروم  ك\u200cتاب") == "میروم ک\u200cتاب"


def test_normalization_is_idempotent_and_preserves_zwnj() -> None:
    value = "می\u200cروم\n\nفیزیک"
    normalized = normalize_persian_text(value)
    assert normalize_persian_text(normalized) == normalized
    assert "\u200c" in normalized


def test_rtl_safety_rejects_directional_controls() -> None:
    assert is_rtl_safe("متن فارسی \u200c")
    assert not is_rtl_safe("متن\u202eناامن")
