"""Secure file signature validation and PDF/DOCX text extraction."""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import docx
import fitz

from app.core.exceptions import ValidationError

SupportedExtension = Literal["pdf", "docx"]

ALLOWED_CONTENT_TYPES: dict[SupportedExtension, frozenset[str]] = {
    "pdf": frozenset({"application/pdf", "application/x-pdf", "application/octet-stream"}),
    "docx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/octet-stream",
        }
    ),
}

MAX_DOCX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    """Sanitized file metadata after signature and size verification."""

    safe_filename: str
    extension: SupportedExtension
    content_type: str
    size_bytes: int
    sha256_hash: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Extracted plain text and page count from a PDF or DOCX document."""

    text: str
    page_count: int


def sanitize_display_filename(filename: str | None) -> str:
    """Strip directory components and control characters from uploaded filename."""
    raw = Path(filename or "resume").name
    cleaned = "".join(ch for ch in raw if ch.isprintable() and ch not in {"/", "\\", "\x00"})
    return (cleaned.strip() or "resume")[:255]


def validate_upload_signature(
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    max_size_bytes: int,
) -> ValidatedUpload:
    """Verify file extension, size limits, and binary magic signature."""
    safe_name = sanitize_display_filename(filename)
    ext = Path(safe_name).suffix.lower().lstrip(".")
    if ext not in ("pdf", "docx"):
        raise ValidationError("Only PDF and DOCX resume files are supported.")

    extension: SupportedExtension = "pdf" if ext == "pdf" else "docx"

    if not data:
        raise ValidationError("Uploaded resume file is empty.")

    if len(data) > max_size_bytes:
        max_mb = round(max_size_bytes / (1024 * 1024), 1)
        raise ValidationError(f"Resume exceeds maximum allowed file size ({max_mb} MB).")

    normalized_ct = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if normalized_ct and normalized_ct not in ALLOWED_CONTENT_TYPES[extension]:
        raise ValidationError(f"Unsupported MIME content type for .{extension}: {normalized_ct}")

    if extension == "pdf":
        if not data[:1024].lstrip().startswith(b"%PDF-"):
            raise ValidationError("File signature does not match a valid PDF document.")
    else:
        _validate_docx_archive(data)

    return ValidatedUpload(
        safe_filename=safe_name,
        extension=extension,
        content_type=normalized_ct or "application/octet-stream",
        size_bytes=len(data),
        sha256_hash=hashlib.sha256(data).hexdigest(),
    )


def _validate_docx_archive(data: bytes) -> None:
    if not data.startswith(b"PK\x03\x04"):
        raise ValidationError("File signature does not match a valid DOCX archive.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            total_uncompressed = sum(info.file_size for info in members)
            if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ValidationError("DOCX uncompressed content exceeds safety limit.")
            names = {info.filename for info in members}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise ValidationError("Archive is not a valid Word DOCX document.")
    except zipfile.BadZipFile as exc:
        raise ValidationError("Corrupted or invalid DOCX archive.") from exc


def extract_text_from_document(
    *,
    extension: SupportedExtension,
    data: bytes,
    max_pages: int = 15,
) -> ParsedDocument:
    """Extract clean text and page count from PDF or DOCX bytes."""
    if extension == "pdf":
        return _extract_pdf_text(data=data, max_pages=max_pages)
    return _extract_docx_text(data=data, max_pages=max_pages)


def _extract_pdf_text(*, data: bytes, max_pages: int) -> ParsedDocument:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValidationError("Failed to parse PDF document.") from exc

    try:
        page_count = doc.page_count
        if page_count == 0:
            raise ValidationError("PDF document contains no pages.")
        if page_count > max_pages:
            raise ValidationError(
                f"Resume exceeds maximum allowed page limit ({max_pages} pages)."
            )

        pages: list[str] = []
        for page in doc:
            text = str(page.get_text("text")).strip()
            if text:
                pages.append(text)
    finally:
        doc.close()

    combined = "\n\n".join(pages).strip()
    if not combined:
        raise ValidationError("No extractable text found in PDF document.")

    return ParsedDocument(text=combined, page_count=page_count)


def _extract_docx_text(*, data: bytes, max_pages: int) -> ParsedDocument:
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ValidationError("Failed to parse DOCX document.") from exc

    blocks: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text:
            blocks.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                blocks.append(" | ".join(dict.fromkeys(cells)))

    combined = "\n".join(blocks).strip()
    if not combined:
        raise ValidationError("No extractable text found in DOCX document.")

    # Estimate logical pages (~500 words per page) for safety enforcement on DOCX files
    word_count = len(combined.split())
    estimated_pages = max(1, (word_count + 499) // 500)
    if estimated_pages > max_pages:
        raise ValidationError(
            f"Resume exceeds maximum allowed length (~{max_pages} pages)."
        )

    return ParsedDocument(text=combined, page_count=estimated_pages)
