from app.services.worksheet import WorksheetQuestion
from app.services.worksheet_pdf import render_worksheet_pdf


def test_render_worksheet_pdf_returns_valid_pdf() -> None:
    content = render_worksheet_pdf("Math", "Solve", [WorksheetQuestion("۲+۲؟")])
    assert content.startswith(b"%PDF-")
    assert content.endswith((b"%%EOF\n", b"%%EOF\r\n"))
