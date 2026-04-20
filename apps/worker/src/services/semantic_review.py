from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from hashlib import sha1
from urllib import error, request

from src.chunking.text import TextChunk
from src.core.config import settings
from src.db.models import Manual


@dataclass(slots=True)
class ChunkReviewSelection:
    chunk_index: int
    reason: str


@dataclass(slots=True)
class ChunkReviewResult:
    chunk_index: int
    page_number: int
    review_status: str
    selected_reason: str | None = None
    action: str | None = None
    reviewer_model: str | None = None
    coherence_score: float | None = None
    completeness_score: float | None = None
    boundary_quality_score: float | None = None
    reason: str | None = None
    raw_response: str | None = None


@dataclass(slots=True)
class ReviewMetricsSummary:
    manual_id: int
    initial_chunk_count: int
    final_chunk_count: int
    reviewed_count: int
    skipped_count: int
    error_count: int
    merge_actions: int
    split_actions: int
    keep_actions: int
    regenerate_actions: int
    applied_autofixes: int
    avg_coherence_score: float | None
    avg_completeness_score: float | None
    avg_boundary_quality_score: float | None
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float


class SemanticReviewError(RuntimeError):
    pass


def _is_suspicious_boundary(text: str) -> bool:
    normalized = text.rstrip()
    if not normalized:
        return False

    if normalized[-1] in {":", ";", "-", "/", "(", "["}:
        return True

    # Heuristic: endings without punctuation tend to indicate hard cuts.
    if normalized[-1].isalnum() and not normalized.endswith((".", "?", "!")):
        return True

    return False


def select_chunks_for_semantic_review(
    chunks: list[TextChunk],
    *,
    min_chars: int,
    max_chars: int,
    sample_rate: float,
    sample_seed: str,
) -> list[ChunkReviewSelection]:
    selections: list[ChunkReviewSelection] = []
    bounded_sample_rate = max(0.0, min(1.0, sample_rate))

    for chunk_index, chunk in enumerate(chunks):
        text = chunk.text.strip()

        if len(text) < min_chars:
            selections.append(
                ChunkReviewSelection(chunk_index=chunk_index, reason="too_short")
            )
            continue

        if len(text) > max_chars:
            selections.append(
                ChunkReviewSelection(chunk_index=chunk_index, reason="too_long")
            )
            continue

        if _is_suspicious_boundary(text):
            selections.append(
                ChunkReviewSelection(
                    chunk_index=chunk_index, reason="suspicious_boundary"
                )
            )
            continue

        if bounded_sample_rate <= 0:
            continue

        digest = sha1(f"{sample_seed}:{chunk_index}".encode("utf-8")).digest()
        threshold = int.from_bytes(digest[:8], "big") / float(2**64)
        if threshold < bounded_sample_rate:
            selections.append(
                ChunkReviewSelection(chunk_index=chunk_index, reason="sampled")
            )

    return selections


def is_manual_eligible_for_semantic_review(manual: Manual) -> bool:
    enabled_languages = [
        value.strip().lower()
        for value in settings.semantic_review_enabled_languages.split(",")
        if value.strip()
    ]
    if enabled_languages and manual.document_language.lower() not in enabled_languages:
        return False

    include_terms = [
        value.strip().lower()
        for value in settings.semantic_review_title_include_terms.split(",")
        if value.strip()
    ]
    if not include_terms:
        return True

    title = manual.title.lower()
    return any(term in title for term in include_terms)


def build_review_metrics_summary(
    *,
    manual_id: int,
    initial_chunk_count: int,
    final_chunk_count: int,
    review_results: list[ChunkReviewResult],
    applied_autofixes: int,
) -> ReviewMetricsSummary:
    reviewed = [
        result for result in review_results if result.review_status == "reviewed"
    ]
    skipped_count = sum(
        1 for result in review_results if result.review_status == "skipped"
    )
    error_count = sum(1 for result in review_results if result.review_status == "error")

    actions = Counter((result.action or "keep") for result in review_results)

    coherence_scores = [
        result.coherence_score
        for result in reviewed
        if result.coherence_score is not None
    ]
    completeness_scores = [
        result.completeness_score
        for result in reviewed
        if result.completeness_score is not None
    ]
    boundary_scores = [
        result.boundary_quality_score
        for result in reviewed
        if result.boundary_quality_score is not None
    ]

    estimated_input_tokens = sum(
        max(1, len(result.raw_response or "") // 4) for result in review_results
    )
    if reviewed:
        estimated_input_tokens = max(
            estimated_input_tokens,
            len(reviewed) * settings.semantic_review_min_chars // 4,
        )
    estimated_output_tokens = len(review_results) * max(
        1, settings.semantic_review_estimated_output_tokens
    )
    estimated_cost_usd = (
        estimated_input_tokens / 1000.0
    ) * settings.semantic_review_cost_input_per_1k_tokens + (
        estimated_output_tokens / 1000.0
    ) * settings.semantic_review_cost_output_per_1k_tokens

    return ReviewMetricsSummary(
        manual_id=manual_id,
        initial_chunk_count=initial_chunk_count,
        final_chunk_count=final_chunk_count,
        reviewed_count=len(reviewed),
        skipped_count=skipped_count,
        error_count=error_count,
        merge_actions=actions.get("merge_with_next", 0),
        split_actions=actions.get("split", 0),
        keep_actions=actions.get("keep", 0),
        regenerate_actions=actions.get("regenerate", 0),
        applied_autofixes=applied_autofixes,
        avg_coherence_score=_avg_or_none(coherence_scores),
        avg_completeness_score=_avg_or_none(completeness_scores),
        avg_boundary_quality_score=_avg_or_none(boundary_scores),
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        estimated_cost_usd=round(estimated_cost_usd, 8),
    )


class GeminiSemanticReviewer:
    def __init__(self) -> None:
        self._api_key = settings.gemini_api_key.strip()
        self._model = settings.gemini_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    def enabled(self) -> bool:
        return bool(self._api_key and self._api_key.lower() != "replace_me")

    def review_chunk(
        self,
        manual: Manual,
        chunk_index: int,
        chunk: TextChunk,
    ) -> ChunkReviewResult:
        if not self.enabled():
            return ChunkReviewResult(
                chunk_index=chunk_index,
                page_number=chunk.page_number,
                review_status="skipped",
                action="keep",
                reviewer_model=self.model,
                reason="Gemini API key no configurada.",
            )

        prompt = self._build_prompt(manual, chunk_index, chunk)
        response_text = self._call_gemini(prompt)

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise SemanticReviewError("Gemini devolvio JSON invalido.") from exc

        return ChunkReviewResult(
            chunk_index=chunk_index,
            page_number=chunk.page_number,
            review_status="reviewed",
            action=str(payload.get("action") or "keep"),
            reviewer_model=self.model,
            coherence_score=_to_float(payload.get("coherence_score")),
            completeness_score=_to_float(payload.get("completeness_score")),
            boundary_quality_score=_to_float(payload.get("boundary_quality")),
            reason=_normalize_text(payload.get("reason")),
            raw_response=response_text,
        )

    def _build_prompt(self, manual: Manual, chunk_index: int, chunk: TextChunk) -> str:
        return "\n".join(
            [
                "Evalua calidad de chunk para retrieval tecnico.",
                "Responde SOLO JSON valido con esta estructura:",
                '{"coherence_score":0.0,"completeness_score":0.0,"boundary_quality":0.0,"action":"keep|merge_with_next|split|regenerate","reason":"texto breve"}',
                "No inventes contenido fuera del chunk.",
                f"manual_title: {manual.title}",
                f"manual_language: {manual.document_language}",
                f"page_number: {chunk.page_number}",
                f"chunk_index: {chunk_index}",
                "chunk_text:",
                chunk.text,
            ]
        )

    def _call_gemini(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )
        body = {
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
            "contents": [{"parts": [{"text": prompt}]}],
        }

        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            method="POST",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise SemanticReviewError(f"Gemini HTTP {exc.code}") from exc
        except error.URLError as exc:
            raise SemanticReviewError("No se pudo conectar a Gemini.") from exc

        parts = raw.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        if not parts:
            raise SemanticReviewError("Gemini no devolvio contenido util.")

        text = parts[0].get("text", "")
        if not text:
            raise SemanticReviewError("Gemini devolvio respuesta vacia.")
        return text


def _normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _avg_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)
