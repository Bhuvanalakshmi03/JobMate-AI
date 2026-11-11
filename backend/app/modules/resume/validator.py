"""Validation and evidence grounding checks for AI-extracted resume data."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ExternalServiceError
from app.modules.resume.schemas import ExtractedFactCandidate, ExtractedResumePayload

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_for_match(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def _is_evidence_grounded(source_text_norm: str, fact: ExtractedFactCandidate) -> bool:
    """Verify whether the fact's evidence excerpt or title actually appears in resume text."""
    excerpt = _normalize_for_match(fact.evidence_excerpt or "")
    if excerpt and len(excerpt) >= 4:
        if excerpt in source_text_norm:
            return True
        tokens = [tok for tok in re.findall(r"[a-z0-9+#.]{3,}", excerpt)]
        if tokens:
            matched = sum(1 for tok in tokens if tok in source_text_norm)
            return matched / len(tokens) >= 0.7

    title_norm = _normalize_for_match(fact.title)
    return bool(title_norm and len(title_norm) >= 2 and title_norm in source_text_norm)


class ResumeExtractionValidator:
    """Validates raw LLM JSON and checks factual grounding against source resume text."""

    def validate(self, *, raw_json: str, source_text: str) -> ExtractedResumePayload:
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()

        try:
            parsed_raw = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ExternalServiceError(
                "AI resume extraction returned malformed JSON."
            ) from exc

        if not isinstance(parsed_raw, dict):
            raise ExternalServiceError("AI resume extraction response must be a JSON object.")

        try:
            payload = ExtractedResumePayload.model_validate(parsed_raw)
        except PydanticValidationError as exc:
            raise ExternalServiceError(
                "AI resume extraction response failed schema validation."
            ) from exc

        normalized_source = _normalize_for_match(source_text)
        grounded_facts: list[ExtractedFactCandidate] = []
        for fact in payload.facts:
            evidence_matched = _is_evidence_grounded(normalized_source, fact)
            adjusted_confidence = (
                fact.confidence if evidence_matched else min(fact.confidence, 0.35)
            )
            enriched_data = dict(fact.structured_data)
            enriched_data["evidence_matched"] = evidence_matched
            grounded_facts.append(
                fact.model_copy(
                    update={
                        "confidence": round(adjusted_confidence, 3),
                        "structured_data": enriched_data,
                    }
                )
            )

        return payload.model_copy(update={"facts": grounded_facts})
