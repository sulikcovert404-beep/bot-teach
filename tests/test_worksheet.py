import pytest

from app.services.worksheet import WorksheetQuestion, render_worksheet


def test_render_worksheet_contains_questions_and_points() -> None:
    result = render_worksheet(
        "برگه تمرین",
        "به پرسش‌ها پاسخ دهید.",
        [WorksheetQuestion("پایتخت ایران چیست؟", 2)],
    )
    assert "# برگه تمرین" in result
    assert "پایتخت ایران چیست؟" in result
    assert "۲ نمره" in result


def test_render_worksheet_rejects_empty_content() -> None:
    with pytest.raises(ValueError):
        render_worksheet("", "دستور", [WorksheetQuestion("سؤال")])
    with pytest.raises(ValueError):
        render_worksheet("عنوان", "دستور", [WorksheetQuestion("سؤال", 0)])
