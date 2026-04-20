from __future__ import annotations

from datetime import UTC, datetime
from time import sleep

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from src.chunking.text import TextChunk, build_text_chunks
from src.core.config import settings
from src.db.models import Manual, ManualChunk, ManualChunkReview
from src.db.session import SessionLocal, initialize_database
from src.parsers.pdf import extract_pdf_text_by_page
from src.services.semantic_review import (
    ChunkReviewResult,
    GeminiSemanticReviewer,
    SemanticReviewError,
    select_chunks_for_semantic_review,
)
from src.services.storage import ManualStorageService, get_manual_storage_service
from src.utils.logging import log


def claim_next_pending_manual(session: Session) -> Manual | None:
    statement = (
        select(Manual)
        .where(Manual.status == "pending")
        .order_by(Manual.created_at.asc(), Manual.id.asc())
    )

    if session.bind and session.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)

    manual = session.scalar(statement)
    if not manual:
        return None

    manual.status = "processing"
    manual.last_error = None
    manual.chunk_count = 0
    manual.indexed_at = None
    session.add(manual)
    session.commit()
    session.refresh(manual)
    return manual


def index_manual_chunks(
    session: Session,
    manual: Manual,
    chunks: list[TextChunk],
    review_results: list[ChunkReviewResult],
) -> None:
    session.execute(delete(ManualChunk).where(ManualChunk.manual_id == manual.id))
    session.execute(
        delete(ManualChunkReview).where(ManualChunkReview.manual_id == manual.id)
    )

    for chunk_index, chunk in enumerate(chunks):
        session.add(
            ManualChunk(
                manual_id=manual.id,
                chunk_index=chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
            )
        )

    for result in review_results:
        session.add(
            ManualChunkReview(
                manual_id=manual.id,
                chunk_index=result.chunk_index,
                page_number=result.page_number,
                review_status=result.review_status,
                selected_reason=result.selected_reason,
                action=result.action,
                reviewer_model=result.reviewer_model,
                coherence_score=result.coherence_score,
                completeness_score=result.completeness_score,
                boundary_quality_score=result.boundary_quality_score,
                reason=result.reason,
                raw_response=result.raw_response,
            )
        )

    manual.status = "indexed"
    manual.chunk_count = len(chunks)
    manual.last_error = None
    manual.indexed_at = datetime.now(UTC)
    session.add(manual)
    session.commit()


def build_chunk_review_observations(
    manual: Manual,
    chunks: list[TextChunk],
    reviewer: GeminiSemanticReviewer,
) -> list[ChunkReviewResult]:
    if not settings.semantic_review_enabled:
        return []

    selections = select_chunks_for_semantic_review(
        chunks,
        min_chars=settings.semantic_review_min_chars,
        max_chars=settings.semantic_review_max_chars,
        sample_rate=settings.semantic_review_sample_rate,
        sample_seed=f"manual:{manual.id}",
    )
    if not selections:
        return []

    selected_by_index = {selection.chunk_index: selection for selection in selections}
    review_results: list[ChunkReviewResult] = []

    for chunk_index, selection in selected_by_index.items():
        chunk = chunks[chunk_index]
        try:
            reviewed = reviewer.review_chunk(manual, chunk_index, chunk)
            reviewed.selected_reason = selection.reason
            review_results.append(reviewed)
        except SemanticReviewError as exc:
            review_results.append(
                ChunkReviewResult(
                    chunk_index=chunk_index,
                    page_number=chunk.page_number,
                    review_status="error",
                    selected_reason=selection.reason,
                    action="keep",
                    reviewer_model=reviewer.model,
                    reason=str(exc),
                )
            )

    return review_results


def mark_manual_failed(session: Session, manual_id: int, reason: str) -> None:
    manual = session.get(Manual, manual_id)
    if not manual:
        return

    manual.status = "failed"
    manual.chunk_count = 0
    manual.last_error = reason
    manual.indexed_at = None
    session.add(manual)
    session.commit()


def process_next_pending_manual(
    session_factory: sessionmaker[Session] = SessionLocal,
    storage_service: ManualStorageService | None = None,
    semantic_reviewer: GeminiSemanticReviewer | None = None,
) -> bool:
    storage = storage_service or get_manual_storage_service()
    reviewer = semantic_reviewer or GeminiSemanticReviewer()

    with session_factory() as session:
        manual = claim_next_pending_manual(session)
        if not manual:
            return False

        log("worker", f"Procesando manual #{manual.id}: {manual.title}")

        try:
            content = storage.download_manual(manual.storage_key)
            page_texts = extract_pdf_text_by_page(content)
            chunks = build_text_chunks(page_texts)

            if not chunks:
                raise ValueError("No se pudo extraer texto util del PDF.")

            review_results = build_chunk_review_observations(manual, chunks, reviewer)
            index_manual_chunks(session, manual, chunks, review_results)
            log(
                "worker",
                (
                    f"Manual #{manual.id} indexado correctamente con {len(chunks)} chunks "
                    f"y {len(review_results)} revisiones semanticas."
                ),
            )
            return True
        except Exception as exc:
            session.rollback()
            reason = str(exc) or "Error no identificado durante la ingesta."
            mark_manual_failed(session, manual.id, reason)
            log("worker", f"Manual #{manual.id} marco fallo de ingesta: {reason}")
            return True


def run_worker_loop(
    session_factory: sessionmaker[Session] = SessionLocal,
    storage_service: ManualStorageService | None = None,
    poll_interval_seconds: int | None = None,
) -> None:
    initialize_database()
    interval = poll_interval_seconds or settings.worker_poll_interval_seconds
    log("worker", "Worker RC7 iniciado. Esperando trabajos de ingesta...")

    while True:
        processed = process_next_pending_manual(session_factory, storage_service)
        if processed:
            continue

        sleep(interval)
        log("worker", "Heartbeat: worker activo.")
