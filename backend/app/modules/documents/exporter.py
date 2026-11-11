"""ATS-friendly Markdown rendering and PDF/DOCX export utilities."""

from __future__ import annotations

import html
import io
import re

import docx
import pymupdf

from app.modules.documents.generator import VerifiedCandidateContext
from app.modules.documents.schemas import (
    ApplicationNoteStructured,
    CoverLetterStructured,
    ExportFormat,
    TailoredResumeStructured,
)


def render_tailored_resume_markdown(
    *,
    candidate: VerifiedCandidateContext,
    structured: TailoredResumeStructured,
) -> str:
    """Render an ATS-friendly Markdown representation of a tailored resume."""
    lines: list[str] = [f"# {candidate.full_name}"]
    contact_parts = [
        part
        for part in (
            candidate.email,
            candidate.location,
            candidate.linkedin_url,
            candidate.github_url,
            candidate.portfolio_url,
        )
        if part
    ]
    if contact_parts:
        lines.append(" | ".join(contact_parts))
    lines.append("")
    lines.extend(["## Professional Summary", structured.summary.strip(), ""])

    if structured.selected_skills:
        lines.extend(["## Technical Skills", ", ".join(structured.selected_skills), ""])

    if structured.experience:
        lines.append("## Experience")
        for exp in structured.experience:
            header = exp.title
            if exp.organization:
                header += f" — {exp.organization}"
            if exp.date_range:
                header += f" ({exp.date_range})"
            lines.append(f"### {header}")
            for bullet in exp.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

    if structured.projects:
        lines.append("## Projects")
        for proj in structured.projects:
            header = proj.title
            if proj.organization:
                header += f" — {proj.organization}"
            if proj.date_range:
                header += f" ({proj.date_range})"
            lines.append(f"### {header}")
            for bullet in proj.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

    if structured.education:
        lines.append("## Education")
        for edu in structured.education:
            parts = [edu.degree]
            if edu.institution:
                parts.append(edu.institution)
            if edu.date_range:
                parts.append(edu.date_range)
            lines.append(f"- {' — '.join(parts)}")
        lines.append("")

    return "\n".join(lines).strip()


def render_cover_letter_markdown(
    *,
    candidate: VerifiedCandidateContext,
    structured: CoverLetterStructured,
) -> str:
    lines: list[str] = [
        f"# {structured.subject.strip()}",
        "",
        structured.salutation.strip(),
        "",
    ]
    for para in structured.paragraphs:
        lines.append(para.strip())
        lines.append("")
    lines.extend([structured.closing.strip(), candidate.full_name])
    return "\n".join(lines).strip()


def render_application_note_markdown(structured: ApplicationNoteStructured) -> str:
    return structured.note.strip()


def _safe_download_filename(title: str, ext: ExportFormat) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", title).strip("._")[:80] or "jobmate_document"
    return f"{slug}.{ext}"


def _markdown_to_html(title: str, markdown_text: str) -> str:
    html_parts: list[str] = [
        "<html><head><style>",
        "body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; "
        "line-height: 1.45; color: #111827; }",
        "h1 { font-size: 16pt; margin: 0 0 6pt 0; color: #0f172a; }",
        "h2 { font-size: 11.5pt; margin: 12pt 0 4pt 0; border-bottom: 1pt solid #cbd5e1; "
        "padding-bottom: 2pt; color: #1e293b; }",
        "h3 { font-size: 10.5pt; margin: 8pt 0 2pt 0; color: #0f172a; }",
        "p { margin: 4pt 0; }",
        "ul { margin: 3pt 0 6pt 14pt; padding: 0; }",
        "li { margin: 2pt 0; }",
        "</style></head><body>",
    ]
    in_list = False
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{html.escape(line[2:].strip())}</li>")
            continue
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        if line.startswith("### "):
            html_parts.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            html_parts.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        else:
            html_parts.append(f"<p>{html.escape(line)}</p>")

    if in_list:
        html_parts.append("</ul>")
    if not markdown_text.strip():
        html_parts.append(f"<h1>{html.escape(title)}</h1>")
    html_parts.append("</body></html>")
    return "".join(html_parts)


def export_document_bytes(
    *,
    title: str,
    content_markdown: str,
    export_format: ExportFormat,
) -> tuple[bytes, str, str]:
    """Export document content to PDF, DOCX, or Markdown bytes with MIME type and safe filename."""
    filename = _safe_download_filename(title, export_format)

    if export_format == "md":
        return content_markdown.encode("utf-8"), "text/markdown; charset=utf-8", filename

    if export_format == "docx":
        document = docx.Document()
        for raw_line in content_markdown.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# "):
                document.add_heading(line[2:].strip(), level=1)
            elif line.startswith("## "):
                document.add_heading(line[3:].strip(), level=2)
            elif line.startswith("### "):
                document.add_heading(line[4:].strip(), level=3)
            elif line.startswith("- ") or line.startswith("* "):
                document.add_paragraph(line[2:].strip(), style="List Bullet")
            else:
                document.add_paragraph(line)
        buf = io.BytesIO()
        document.save(buf)
        return (
            buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename,
        )

    # ATS-friendly searchable PDF via PyMuPDF Story
    html_doc = _markdown_to_html(title, content_markdown)
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)  # type: ignore[no-untyped-call]
    story = pymupdf.Story(html_doc)  # type: ignore[no-untyped-call]
    mediabox = pymupdf.paper_rect("letter")
    where = mediabox + (42, 42, -42, -42)
    more = 1
    while more:
        device = writer.begin_page(mediabox)  # type: ignore[no-untyped-call]
        more, _ = story.place(where)  # type: ignore[no-untyped-call]
        story.draw(device, None)  # type: ignore[no-untyped-call]
        writer.end_page()  # type: ignore[no-untyped-call]
    writer.close()  # type: ignore[no-untyped-call]
    return buf.getvalue(), "application/pdf", filename
