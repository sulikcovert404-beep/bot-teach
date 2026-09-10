"""Minimal, controlled admin content ingestion for Phase 1.

The endpoint stores an immutable source snapshot and extracted text as a draft;
AI generation and automatic publication are deliberately outside this gate.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import time
import zipfile
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import Book, Chapter, ContentVersion, Lesson, SourceChunk, SourceDocument
from app.security.dependencies import require_roles

router = APIRouter(prefix="/admin/content", tags=["admin-content"])
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("PDF_MAX_PAGES", "500"))
PDF_EXTRACTION_TIMEOUT_SECONDS = float(os.getenv("PDF_EXTRACTION_TIMEOUT_SECONDS", "30"))
PDF_CHUNK_CHARS = 8_000
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
logger = logging.getLogger(__name__)


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise HTTPException(503, "PDF extraction dependency unavailable") from exc
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if len(reader.pages) > MAX_PDF_PAGES:
            raise HTTPException(422, "PDF exceeds the page limit")
        pages = []
        started = time.monotonic()
        for page_number, page in enumerate(reader.pages, start=1):
            if time.monotonic() - started > PDF_EXTRACTION_TIMEOUT_SECONDS:
                raise HTTPException(422, "PDF extraction timed out")
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                logger.warning("PDF page extraction failed", extra={"page": page_number})
                pages.append("")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "Invalid PDF document") from exc
    return "\n\n".join(pages).strip()


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise HTTPException(422, "Invalid DOCX document") from exc
    root = ElementTree.fromstring(xml)
    return "\n".join(
        "".join(node.itertext()).strip()
        for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
        if "".join(node.itertext()).strip()
    )


def _extract(filename: str, data: bytes) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "pdf":
        return _extract_pdf(data)
    if suffix == "docx":
        return _extract_docx(data)
    raise HTTPException(415, "Only PDF and DOCX files are supported")


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_content(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    grade: str = Form(..., min_length=1, max_length=64),
    subject: str = Form(..., min_length=1, max_length=128),
    chapter_title: str = Form(default="محتوای استخراج‌شده", max_length=255),
    lesson_title: str = Form(default="درس اول", max_length=255),
    actor: str = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    filename = _SAFE_NAME.sub("_", file.filename or "upload").strip("._") or "upload"
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds the configured upload limit")
    if file.content_type not in {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
        raise HTTPException(415, "Unsupported MIME type")
    text = _extract(filename, data)
    if not text:
        state = "EXTRACTION_REVIEW_REQUIRED"
    else:
        state = "PROCESSED"
    digest = hashlib.sha256(data).hexdigest()
    source = await session.scalar(
        select(SourceDocument).where(SourceDocument.source_id == f"upload:{digest}")
    )
    if source is None:
        source = SourceDocument(source_id=f"upload:{digest}", title=title, uri=filename)
        session.add(source)
        await session.flush()
    version_number = (await session.scalar(
        select(func.max(ContentVersion.version_number)).where(
            ContentVersion.source_document_id == source.id
        )
    ) or 0) + 1
    book = await session.scalar(
        select(Book).where(Book.title == title, Book.grade == grade, Book.subject == subject)
    )
    if book is None:
        book = Book(title=title, grade=grade, subject=subject)
        session.add(book)
        await session.flush()
    chapter = Chapter(book_id=book.id, title=chapter_title, position=0)
    session.add(chapter)
    await session.flush()
    session.add(Lesson(chapter_id=chapter.id, title=lesson_title, position=0))
    version = ContentVersion(
        source_document_id=source.id,
        version_number=version_number,
        processing_state=state,
        review_state="DRAFT",
        source_hash=digest,
        extracted_hash=hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
        provenance_json='{"upload": "admin", "filename_sanitized": true}',
    )
    session.add(version)
    if text:
        for chunk_index, start in enumerate(range(0, len(text), PDF_CHUNK_CHARS)):
            chunk_text = text[start : start + PDF_CHUNK_CHARS]
            session.add(SourceChunk(
                document_id=source.id,
                chunk_index=chunk_index,
                text=chunk_text,
                book_id=book.id,
                grade=grade,
                subject=subject,
                content_hash=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
            ))
    await session.commit()
    return {"source_id": source.source_id, "book_id": book.id, "content_version_id": version.id, "processing_state": state, "review_state": "DRAFT", "extracted": bool(text)}
