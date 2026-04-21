from __future__ import annotations

import signal
from contextlib import contextmanager
from datetime import UTC, datetime
from math import ceil
from time import sleep

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from src.chunking.text import TextChunk, build_text_chunks
from src.core.config import settings
from src.db.models import Manual, ManualChunk, ManualChunkReview, ManualReviewSummary
from src.db.session import SessionLocal, initialize_database
from src.parsers.pdf import extract_pdf_text_by_page
from src.services.semantic_review import (
    ChunkReviewResult,
    GeminiSemanticReviewer,
    ReviewMetricsSummary,
    SemanticReviewError,
    build_review_metrics_summary,
    is_manual_eligible_for_semantic_review,
    select_chunks_for_semantic_review,
)
from src.services.storage import ManualStorageService, get_manual_storage_service
from src.utils.logging import log


class ManualProcessingTimeoutError(TimeoutError):
    pass


def calculate_manual_timeout_seconds(manual: Manual) -> int:
    base_timeout = max(1, settings.worker_manual_timeout_seconds)
    base_coverage_mb = max(1, settings.worker_manual_timeout_base_coverage_mb)
    extra_per_mb = max(0, settings.worker_manual_timeout_extra_per_mb_seconds)
    max_timeout = max(base_timeout, settings.worker_manual_timeout_max_seconds)

    size_bytes = max(0, int(manual.size_bytes or 0))
    if size_bytes == 0 or extra_per_mb == 0:
        return min(base_timeout, max_timeout)

    size_mb = ceil(size_bytes / float(1024 * 1024))
    extra_mb = max(0, size_mb - base_coverage_mb)
    computed_timeout = base_timeout + (extra_mb * extra_per_mb)
    return min(computed_timeout, max_timeout)


@contextmanager
def manual_processing_timeout(timeout_seconds: int):
    if timeout_seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handle_alarm(_signum, _frame):
        raise ManualProcessingTimeoutError(
            f"Tiempo maximo de procesamiento excedido ({timeout_seconds}s)."
        )

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handle_alarm)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _append_reason(reason: str | None, suffix: str) -> str:
    base = (reason or "").strip()
    return f"{base} {suffix}".strip() if base else suffix


def _split_text_for_autofix(text: str) -> tuple[str, str] | None:
    if len(text) < 2:
        return None

    midpoint = len(text) // 2
    split_index = text.rfind("\n\n", 0, midpoint + 1)
    separator_len = 2

    if split_index == -1:
        split_index = text.rfind(". ", 0, midpoint + 1)
        separator_len = 2

    if split_index == -1:
        split_index = midpoint
        separator_len = 0

    left = text[:split_index].strip()
    right = text[split_index + separator_len :].strip()
    if not left or not right:
        return None
    return left, right


def apply_safe_chunk_autofixes(
    chunks: list[TextChunk],
    review_results: list[ChunkReviewResult],
) -> tuple[list[TextChunk], int]:
    if not settings.semantic_review_autofix_enabled:
        return chunks, 0

    review_by_index = {result.chunk_index: result for result in review_results}
    fixed_chunks: list[TextChunk] = []
    applied_count = 0

    index = 0
    while index < len(chunks):
        chunk = chunks[index]
        review = review_by_index.get(index)

        if (
            review
            and review.action == "merge_with_next"
            and index + 1 < len(chunks)
            and chunk.page_number == chunks[index + 1].page_number
            and (review.boundary_quality_score is not None)
            and review.boundary_quality_score
            <= settings.semantic_review_merge_boundary_max
        ):
            merged_text = (
                f"{chunk.text.rstrip()}\n\n{chunks[index + 1].text.lstrip()}".strip()
            )
            fixed_chunks.append(
                TextChunk(page_number=chunk.page_number, text=merged_text)
            )
            review.reason = _append_reason(
                review.reason, "Auto-fix aplicado: merge_with_next."
            )
            applied_count += 1
            index += 2
            continue

        if (
            review
            and review.action == "split"
            and len(chunk.text) >= settings.semantic_review_split_min_chars
            and (review.coherence_score is not None)
            and review.coherence_score <= settings.semantic_review_split_max_coherence
        ):
            split_pair = _split_text_for_autofix(chunk.text)
            if split_pair:
                left, right = split_pair
                fixed_chunks.append(TextChunk(page_number=chunk.page_number, text=left))
                fixed_chunks.append(
                    TextChunk(page_number=chunk.page_number, text=right)
                )
                review.reason = _append_reason(
                    review.reason, "Auto-fix aplicado: split."
                )
                applied_count += 1
                index += 1
                continue

        fixed_chunks.append(chunk)
        index += 1

    return fixed_chunks, applied_count


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
    manual.processing_started_at = datetime.now(UTC)
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
    summary: ReviewMetricsSummary,
) -> None:
    session.execute(delete(ManualChunk).where(ManualChunk.manual_id == manual.id))
    session.execute(
        delete(ManualChunkReview).where(ManualChunkReview.manual_id == manual.id)
    )
    session.execute(
        delete(ManualReviewSummary).where(ManualReviewSummary.manual_id == manual.id)
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

    session.add(
        ManualReviewSummary(
            manual_id=summary.manual_id,
            initial_chunk_count=summary.initial_chunk_count,
            final_chunk_count=summary.final_chunk_count,
            reviewed_count=summary.reviewed_count,
            skipped_count=summary.skipped_count,
            error_count=summary.error_count,
            merge_actions=summary.merge_actions,
            split_actions=summary.split_actions,
            keep_actions=summary.keep_actions,
            regenerate_actions=summary.regenerate_actions,
            applied_autofixes=summary.applied_autofixes,
            avg_coherence_score=summary.avg_coherence_score,
            avg_completeness_score=summary.avg_completeness_score,
            avg_boundary_quality_score=summary.avg_boundary_quality_score,
            estimated_input_tokens=summary.estimated_input_tokens,
            estimated_output_tokens=summary.estimated_output_tokens,
            estimated_cost_usd=summary.estimated_cost_usd,
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
    if not is_manual_eligible_for_semantic_review(manual):
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

    max_reviews = settings.semantic_review_max_reviews_per_manual
    if max_reviews > 0 and len(selections) > max_reviews:
        _REVIEW_PRIORITY: dict[str, int] = {
            "suspicious_boundary": 0,
            "too_long": 1,
            "sampled": 2,
            "too_short": 3,
        }
        selections.sort(key=lambda s: _REVIEW_PRIORITY.get(s.reason, 99))
        selections = selections[:max_reviews]
        selections.sort(key=lambda s: s.chunk_index)

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


def recover_stuck_processing_manuals(
    session_factory: sessionmaker[Session] = SessionLocal,
) -> int:
    with session_factory() as session:
        stuck_manuals = list(
            session.scalars(select(Manual).where(Manual.status == "processing"))
        )

        if not stuck_manuals:
            return 0

        for manual in stuck_manuals:
            manual.status = "pending"
            manual.chunk_count = 0
            manual.processing_started_at = None
            manual.indexed_at = None
            manual.last_error = "Reencolado automaticamente tras reinicio del worker."
            session.add(manual)

        session.commit()
        return len(stuck_manuals)


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
            timeout_seconds = calculate_manual_timeout_seconds(manual)
            with manual_processing_timeout(timeout_seconds):
                content = storage.download_manual(manual.storage_key)
                page_texts = extract_pdf_text_by_page(content)
                chunks = build_text_chunks(page_texts)

                if not chunks:
                    raise ValueError("No se pudo extraer texto util del PDF.")

                review_results = build_chunk_review_observations(
                    manual, chunks, reviewer
                )
                fixed_chunks, applied_autofixes = apply_safe_chunk_autofixes(
                    chunks, review_results
                )

                summary = build_review_metrics_summary(
                    manual_id=manual.id,
                    initial_chunk_count=len(chunks),
                    final_chunk_count=len(fixed_chunks),
                    review_results=review_results,
                    applied_autofixes=applied_autofixes,
                )
                index_manual_chunks(
                    session, manual, fixed_chunks, review_results, summary
                )
                log(
                    "worker",
                    (
                        f"Manual #{manual.id} indexado con {len(fixed_chunks)} chunks, "
                        f"{len(review_results)} revisiones semanticas y "
                        f"{applied_autofixes} auto-fixes. costo_estimado=${summary.estimated_cost_usd:.6f}"
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
    recovered_count = 0
    if session_factory is not None:
        recovered_count = recover_stuck_processing_manuals(session_factory)
    interval = poll_interval_seconds or settings.worker_poll_interval_seconds
    log("worker", "Worker RC7 iniciado. Esperando trabajos de ingesta...")
    if recovered_count > 0:
        log(
            "worker",
            f"Se reencolaron {recovered_count} manual(es) que quedaron en processing.",
        )

    while True:
        processed = process_next_pending_manual(session_factory, storage_service)
        if processed:
            continue

        sleep(interval)
        log("worker", "Heartbeat: worker activo.")
