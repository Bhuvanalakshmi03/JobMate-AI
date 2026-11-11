"""Resume file validation and text extraction service wrapper."""

from __future__ import annotations

from app.core.config import Settings
from app.integrations.document_parser.extractor import (
    ParsedDocument,
    SupportedExtension,
    ValidatedUpload,
    extract_text_from_document,
    validate_upload_signature,
)


class ResumeParser:
    """Validates uploaded resume files and extracts clean text."""

    def __init__(self, settings: Settings) -> None:
        self._max_size_bytes = settings.max_resume_size_bytes
        self._max_pages = settings.max_resume_pages

    def validate(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        data: bytes,
    ) -> ValidatedUpload:
        """Verify extension, size bounds, MIME type, and file signature."""
        return validate_upload_signature(
            filename=filename,
            content_type=content_type,
            data=data,
            max_size_bytes=self._max_size_bytes,
        )

    def parse(self, *, extension: SupportedExtension, data: bytes) -> ParsedDocument:
        """Extract plain text and page count from validated PDF or DOCX bytes."""
        return extract_text_from_document(
            extension=extension,
            data=data,
            max_pages=self._max_pages,
        )
