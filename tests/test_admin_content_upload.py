from pathlib import Path

import pytest

from app.api.routes.admin_content import _extract_docx, _extract_pdf


FIXTURES = Path(__file__).parent / "fixtures"


def test_pdf_fixture_extracts_persian_text():
    pytest.importorskip("pypdf")
    text = _extract_pdf((FIXTURES / "content_upload_test_book_fa.pdf").read_bytes())
    # PDF text extraction may expose RTL glyph order reversed by the PDF text map.
    assert "کتاب آزمایشی آموزش" in text or "شزومآ یشیامزآ باتک" in text
    assert "فصل اول" in text or "لوا لصف" in text


def test_docx_fixture_extracts_paragraphs():
    text = _extract_docx((FIXTURES / "content_upload_test_book_fa.docx").read_bytes())
    assert "کتاب آزمایشی آموزش" in text
    assert "پاراگراف دوم" in text


def test_invalid_docx_is_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        _extract_docx(b"not-a-docx")
    assert error.value.status_code == 422
