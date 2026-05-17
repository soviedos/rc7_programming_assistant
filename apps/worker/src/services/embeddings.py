"""Gemini text-embedding service used during chunk indexing."""

from __future__ import annotations

import time
from typing import Sequence

from google import genai
from google.genai import types

from src.core.config import settings
from src.utils.logging import log

_EMBEDDING_MODEL = "gemini-embedding-001"
_BATCH_SIZE = 100  # max texts per batch call
_RETRY_LIMIT = 3
_RETRY_BACKOFF = 2.0  # seconds


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Return one embedding vector per input text (dimension 768).

    Processes in batches and retries on transient errors.
    Returns an empty list for each text that ultimately fails.
    """
    client = _get_client()
    results: list[list[float]] = []

    for batch_start in range(0, len(texts), _BATCH_SIZE):
        batch = list(texts[batch_start : batch_start + _BATCH_SIZE])
        for attempt in range(1, _RETRY_LIMIT + 1):
            try:
                response = client.models.embed_content(
                    model=_EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                results.extend([list(e.values) for e in response.embeddings])
                break
            except Exception as exc:
                if attempt == _RETRY_LIMIT:
                    log(
                        "worker",
                        f"Fallo al generar embeddings (batch {batch_start}): {exc}. "
                        "Se guardaran como NULL.",
                    )
                    results.extend([[] for _ in batch])
                else:
                    wait = _RETRY_BACKOFF * attempt
                    log(
                        "worker",
                        f"Error al generar embeddings (intento {attempt}/{_RETRY_LIMIT}): {exc}. "
                        f"Reintentando en {wait:.1f}s…",
                    )
                    time.sleep(wait)

    return results
