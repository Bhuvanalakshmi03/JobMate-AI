"""Deterministic text normalization, chunking, content hashing, and prompt-injection guards."""

from __future__ import annotations

import hashlib
import re

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")
_INJECTION_LINE_RE = re.compile(
    r"(?i)^\s*(ignore\s+(all\s+)?previous\s+instructions|system\s*:|assistant\s*:|<\s*/?\s*system\s*>)"
)


def clean_text(raw_text: str) -> str:
    """Normalize control characters and excessive whitespace while preserving readability."""
    cleaned = _CONTROL_CHAR_RE.sub(" ", raw_text or "")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def content_sha256(text: str) -> str:
    """Compute canonical SHA-256 content hash for deduplicating embedding generation."""
    normalized = clean_text(text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def chunk_text(
    text: str,
    *,
    max_chars: int = 800,
    overlap_chars: int = 120,
) -> list[str]:
    """Split normalized text into bounded, overlapping chunks along word boundaries."""
    normalized = clean_text(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    step_overlap = min(overlap_chars, max_chars // 3)
    while start < len(normalized):
        end = min(len(normalized), start + max_chars)
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + max_chars // 2, end)
            if boundary > start:
                end = boundary
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = max(start + 1, end - step_overlap)
    return chunks


def sanitize_untrusted_context(text: str, *, max_chars: int = 1500) -> str:
    """Strip suspicious instruction-override lines from retrieved text before LLM prompting."""
    safe_lines: list[str] = []
    for line in (text or "").splitlines():
        if _INJECTION_LINE_RE.match(line):
            continue
        cleaned = _CONTROL_CHAR_RE.sub(" ", line).strip()
        if cleaned:
            safe_lines.append(cleaned)
    joined = "\n".join(safe_lines)
    if len(joined) > max_chars:
        return joined[:max_chars].rstrip() + "..."
    return joined
