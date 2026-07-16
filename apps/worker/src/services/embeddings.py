"""Gemini text-embedding service used during chunk indexing."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Sequence

from google import genai
from google.genai import types
from rc7_shared_config import PLACEHOLDER

from src.core.config import settings
from src.utils.logging import log

_EMBEDDING_MODEL = settings.gemini_embed_model
_OUTPUT_DIMENSIONALITY = settings.gemini_embed_dim  # must match the API's value
_BATCH_SIZE = 100  # max texts per batch call
_RETRY_LIMIT = 3
_RETRY_BACKOFF = 2.0  # seconds


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=settings.gemini_timeout_seconds * 1000,  # SDK expects ms
        ),
    )


def embed_texts(
    texts: Sequence[str],
    titles: Sequence[str | None] | None = None,
) -> list[list[float]]:
    """Return one embedding vector per input text (dimension _OUTPUT_DIMENSIONALITY).

    ``titles`` is the section each text belongs to; se envía a Gemini como el
    campo ``title`` del prefijo, que es contexto real para el embedding en lugar
    del "none" que se mandaba antes. Si falta, se cae a "none".

    Processes in batches and retries on transient errors.
    Returns an empty list for each text that ultimately fails.
    """
    if settings.gemini_api_key.strip() in {PLACEHOLDER, ""}:
        # Without this the batch would retry three times and store NULL embeddings
        # without ever saying why.
        log("worker", "GEMINI_API_KEY no configurada: no se generaran embeddings.")
        return [[] for _ in texts]

    client = _get_client()
    results: list[list[float]] = []
    section_titles = list(titles or [None] * len(texts))

    for batch_start in range(0, len(texts), _BATCH_SIZE):
        batch = list(texts[batch_start : batch_start + _BATCH_SIZE])
        batch_titles = section_titles[batch_start : batch_start + _BATCH_SIZE]
        for attempt in range(1, _RETRY_LIMIT + 1):
            try:
                contents = [
                    types.Content(
                        parts=[
                            types.Part.from_text(
                                text=f"title: {title or 'none'} | text: {t}"
                            )
                        ]
                    )
                    for t, title in zip(batch, batch_titles)
                ]
                response = client.models.embed_content(
                    model=_EMBEDDING_MODEL,
                    contents=contents,
                    config=types.EmbedContentConfig(
                        output_dimensionality=_OUTPUT_DIMENSIONALITY
                    ),
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
