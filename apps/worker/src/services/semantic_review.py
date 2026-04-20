from __future__ import annotations

import json
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
