"""Factuality and anti-hallucination validator for AI-generated career documents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ExternalServiceError, ValidationError
from app.modules.documents.generator import JobTargetContext, VerifiedCandidateContext
from app.modules.documents.schemas import (
    ApplicationNoteStructured,
    CoverLetterStructured,
    TailoredResumeStructured,
)
from app.modules.matching.scorer import normalize_skill

_METRIC_TOKEN_RE = re.compile(
    r"(?:\$\s*\d+(?:[.,]\d+)?\s*[kKmMbB]?|\b\d+(?:\.\d+)?%|\b\d+(?:\.\d+)?x\b)"
)


def _strip_json_fence(raw_json: str) -> str:
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()
    return cleaned


def _parse_json_dict(raw_json: str) -> dict[str, Any]:
    try:
        parsed = json.loads(_strip_json_fence(raw_json))
    except json.JSONDecodeError as exc:
        raise ExternalServiceError("AI document generator returned malformed JSON.") from exc
    if not isinstance(parsed, dict):
        raise ExternalServiceError("AI document generator response must be a JSON object.")
    return parsed


@dataclass(frozen=True, slots=True)
class FactualityCheckResult:
    """Structured factuality audit attached to each generated document."""

    is_grounded: bool
    verified_fact_ids: list[str]
    checked_claims_count: int
    unsupported_claims: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_grounded": self.is_grounded,
            "verified_fact_ids": self.verified_fact_ids,
            "checked_claims_count": self.checked_claims_count,
            "unsupported_claims": self.unsupported_claims,
        }


class DocumentFactualityValidator:
    """Verifies generated resumes, cover letters, and notes against verified facts."""

    def _build_trusted_corpus(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
    ) -> tuple[str, set[str], set[str], set[str]]:
        text_parts: list[str] = [
            candidate.full_name,
            candidate.headline or "",
            candidate.summary or "",
            candidate.university or "",
            candidate.degree or "",
            str(candidate.graduation_year or ""),
            job.title,
            job.company,
            job.location or "",
        ]
        allowed_orgs: set[str] = set()
        if candidate.university:
            allowed_orgs.add(candidate.university.strip().lower())

        allowed_skills: set[str] = {
            normalize_skill(s) for s in candidate.verified_skills if s.strip()
        }

        for fact in candidate.verified_facts:
            title = str(fact.get("title") or "").strip()
            org = str(fact.get("organization") or "").strip()
            desc = str(fact.get("description") or "").strip()
            text_parts.extend(
                [
                    title,
                    org,
                    desc,
                    str(fact.get("start_date") or ""),
                    str(fact.get("end_date") or ""),
                ]
            )
            if org:
                allowed_orgs.add(org.lower())
            if fact.get("fact_type") == "skill" and title:
                allowed_skills.add(normalize_skill(title))

        full_corpus = "\n".join(text_parts)
        allowed_metrics = {
            m.group(0).lower().replace(" ", "") for m in _METRIC_TOKEN_RE.finditer(full_corpus)
        }
        return full_corpus.lower(), allowed_skills, allowed_orgs, allowed_metrics

    def _find_unsupported_metrics(self, texts: list[str], allowed_metrics: set[str]) -> list[str]:
        unsupported: list[str] = []
        for text in texts:
            for match in _METRIC_TOKEN_RE.finditer(text):
                token = match.group(0)
                normalized = token.lower().replace(" ", "")
                if normalized not in allowed_metrics:
                    unsupported.append(f"Unverified numerical metric '{token}'")
        return unsupported

    def validate_tailored_resume(
        self,
        *,
        raw_json: str,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
    ) -> tuple[TailoredResumeStructured, FactualityCheckResult]:
        parsed = _parse_json_dict(raw_json)
        try:
            structured = TailoredResumeStructured.model_validate(parsed)
        except PydanticValidationError as exc:
            raise ExternalServiceError(
                "Generated tailored resume failed structured schema validation."
            ) from exc

        corpus_lower, allowed_skills, allowed_orgs, allowed_metrics = self._build_trusted_corpus(
            candidate=candidate,
            job=job,
        )
        unsupported: list[str] = []
        checked = 0

        for skill in structured.selected_skills:
            checked += 1
            norm = normalize_skill(skill)
            if norm not in allowed_skills and norm not in corpus_lower:
                unsupported.append(f"Unverified skill '{skill}'")

        for entry in structured.experience + structured.projects:
            if entry.organization and entry.organization.strip():
                checked += 1
                org_norm = entry.organization.strip().lower()
                if org_norm not in allowed_orgs and org_norm not in corpus_lower:
                    unsupported.append(f"Unverified organization '{entry.organization}'")
            checked += len(entry.bullets)
            unsupported.extend(self._find_unsupported_metrics(entry.bullets, allowed_metrics))

        for edu in structured.education:
            if edu.institution and edu.institution.strip():
                checked += 1
                inst_norm = edu.institution.strip().lower()
                if inst_norm not in allowed_orgs and inst_norm not in corpus_lower:
                    unsupported.append(f"Unverified institution '{edu.institution}'")

        unsupported.extend(self._find_unsupported_metrics([structured.summary], allowed_metrics))

        if unsupported:
            raise ValidationError(
                "Generated tailored resume contains unsupported factual claims: "
                + "; ".join(unsupported[:5]),
                details={"unsupported_claims": unsupported},
            )

        report = FactualityCheckResult(
            is_grounded=True,
            verified_fact_ids=list(candidate.verified_fact_ids),
            checked_claims_count=max(1, checked),
            unsupported_claims=[],
        )
        return structured, report

    def validate_cover_letter(
        self,
        *,
        raw_json: str,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
    ) -> tuple[CoverLetterStructured, FactualityCheckResult]:
        parsed = _parse_json_dict(raw_json)
        try:
            structured = CoverLetterStructured.model_validate(parsed)
        except PydanticValidationError as exc:
            raise ExternalServiceError(
                "Generated cover letter failed structured schema validation."
            ) from exc

        _, _, _, allowed_metrics = self._build_trusted_corpus(candidate=candidate, job=job)
        unsupported = self._find_unsupported_metrics(
            [structured.subject, *structured.paragraphs],
            allowed_metrics,
        )
        if unsupported:
            raise ValidationError(
                "Generated cover letter contains unsupported metrics: "
                + "; ".join(unsupported[:5]),
                details={"unsupported_claims": unsupported},
            )

        report = FactualityCheckResult(
            is_grounded=True,
            verified_fact_ids=list(candidate.verified_fact_ids),
            checked_claims_count=len(structured.paragraphs),
            unsupported_claims=[],
        )
        return structured, report

    def validate_application_note(
        self,
        *,
        raw_json: str,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
    ) -> tuple[ApplicationNoteStructured, FactualityCheckResult]:
        parsed = _parse_json_dict(raw_json)
        try:
            structured = ApplicationNoteStructured.model_validate(parsed)
        except PydanticValidationError as exc:
            raise ExternalServiceError(
                "Generated application note failed structured schema validation."
            ) from exc

        _, _, _, allowed_metrics = self._build_trusted_corpus(candidate=candidate, job=job)
        unsupported = self._find_unsupported_metrics([structured.note], allowed_metrics)
        if unsupported:
            raise ValidationError(
                "Generated application note contains unsupported metrics: "
                + "; ".join(unsupported[:5]),
                details={"unsupported_claims": unsupported},
            )

        report = FactualityCheckResult(
            is_grounded=True,
            verified_fact_ids=list(candidate.verified_fact_ids),
            checked_claims_count=1,
            unsupported_claims=[],
        )
        return structured, report
