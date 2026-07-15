"""Re-generate embeddings for all manual_chunks that have NULL embedding.

Usage (inside the worker container or with the worker venv active):
    python -m scripts.reembed_chunks

The script processes chunks in batches of 100. Retries are handled inside
embed_texts (3 attempts with backoff per batch); a batch that still fails leaves
its embeddings as NULL. Exits with code 1 if any batch could not be embedded.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from src.db.models import ManualChunk
from src.db.session import SessionLocal, initialize_database
from src.services.embeddings import embed_texts
from src.utils.logging import log

_BATCH_SIZE = 100


def reembed_all_missing() -> None:
    initialize_database()
    session = SessionLocal()
    errors = 0

    try:
        total = (
            session.execute(
                select(ManualChunk.id).where(ManualChunk.embedding.is_(None))
            )
            .scalars()
            .all()
        )

        if not total:
            log("reembed", "No hay chunks sin embedding. Nada que hacer.")
            return

        log(
            "reembed",
            f"Chunks sin embedding: {len(total)}. Generando en lotes de {_BATCH_SIZE}...",
        )

        for batch_start in range(0, len(total), _BATCH_SIZE):
            batch_ids = total[batch_start : batch_start + _BATCH_SIZE]

            chunks: list[ManualChunk] = (
                session.execute(
                    select(ManualChunk).where(ManualChunk.id.in_(batch_ids))
                )
                .scalars()
                .all()
            )

            texts = [c.text for c in chunks]
            embeddings = embed_texts(texts)

            if not embeddings or all(len(e) == 0 for e in embeddings):
                log(
                    "reembed",
                    f"  Lote {batch_start // _BATCH_SIZE + 1}: fallo al generar embeddings. Se omite.",
                )
                errors += 1
                continue

            for chunk, embedding in zip(chunks, embeddings):
                if embedding:
                    chunk.embedding = embedding

            session.commit()
            done = min(batch_start + _BATCH_SIZE, len(total))
            log(
                "reembed",
                f"  Lote {batch_start // _BATCH_SIZE + 1}: {done}/{len(total)} chunks embebidos.",
            )

        log("reembed", f"Re-embedding completado. Errores en lotes: {errors}.")

    finally:
        session.close()

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    reembed_all_missing()
