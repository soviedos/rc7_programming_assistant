import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Manual, ManualChunk, ManualChunkReview, ManualReviewSummary
from src.chunking.text import TextChunk
from src.jobs.ingestion import (
    apply_safe_chunk_autofixes,
    process_next_pending_manual,
    run_worker_loop,
)
from src.services.semantic_review import ChunkReviewResult


class FakeStorageService:
    def __init__(self, content: bytes = b"%PDF-1.4 fake") -> None:
        self.content = content
        self.keys: list[str] = []

    def download_manual(self, storage_key: str) -> bytes:
        self.keys.append(storage_key)
        return self.content


class FakeSemanticReviewer:
    model = "fake-reviewer"

    def review_chunk(
        self, manual: Manual, chunk_index: int, chunk
    ) -> ChunkReviewResult:  # type: ignore[no-untyped-def]
        return ChunkReviewResult(
            chunk_index=chunk_index,
            page_number=chunk.page_number,
            review_status="reviewed",
            action="keep",
            reviewer_model=self.model,
            coherence_score=0.9,
            completeness_score=0.9,
            boundary_quality_score=0.9,
            reason=f"ok-{manual.id}-{chunk_index}",
            raw_response='{"action":"keep"}',
        )


class ActionSemanticReviewer:
    model = "action-reviewer"

    def __init__(self, actions: dict[int, str]) -> None:
        self.actions = actions

    def review_chunk(
        self, manual: Manual, chunk_index: int, chunk
    ) -> ChunkReviewResult:  # type: ignore[no-untyped-def]
        return ChunkReviewResult(
            chunk_index=chunk_index,
            page_number=chunk.page_number,
            review_status="reviewed",
            action=self.actions.get(chunk_index, "keep"),
            reviewer_model=self.model,
            coherence_score=0.5,
            completeness_score=0.9,
            boundary_quality_score=0.4,
            reason=f"review-{manual.id}-{chunk_index}",
            raw_response='{"action":"keep"}',
        )


def create_manual(db_session: Session, *, status: str = "pending") -> Manual:
    manual = Manual(
        title="RC7 Manual",
        original_filename="manual.pdf",
        storage_key="manuals/2026/04/20/manual.pdf",
        content_type="application/pdf",
        size_bytes=128,
        status=status,
        chunk_count=0,
        robot_model="VP-6242",
        controller_version="RC7.2",
        document_language="en",
        notes=None,
        last_error=None,
        uploaded_by_user_id=1,
        uploaded_by_email="admin@ucenfotec.ac.cr",
        indexed_at=None,
    )
    db_session.add(manual)
    db_session.commit()
    db_session.refresh(manual)
    return manual


def test_process_next_pending_manual_indexes_chunks(
    session_factory,
    db_session: Session,
    monkeypatch,
) -> None:
    manual = create_manual(db_session)
    storage = FakeStorageService()

    monkeypatch.setattr(
        "src.jobs.ingestion.extract_pdf_text_by_page",
        lambda content: ["MOVE P, HOME\n\nWAIT SIG(1)", "CALL PICK_PART"],
    )

    processed = process_next_pending_manual(
        session_factory,
        storage,
        semantic_reviewer=FakeSemanticReviewer(),
    )

    assert processed is True
    assert storage.keys == ["manuals/2026/04/20/manual.pdf"]

    with session_factory() as session:
        refreshed_manual = session.get(Manual, manual.id)
        assert refreshed_manual is not None
        assert refreshed_manual.status == "indexed"
        assert refreshed_manual.chunk_count == 2
        assert refreshed_manual.last_error is None
        assert refreshed_manual.indexed_at is not None

        chunks = list(
            session.scalars(
                select(ManualChunk)
                .where(ManualChunk.manual_id == manual.id)
                .order_by(ManualChunk.chunk_index.asc())
            )
        )
        assert len(chunks) == 2
        assert chunks[0].page_number == 1
        assert chunks[0].text == "MOVE P, HOME\n\nWAIT SIG(1)"
        assert chunks[1].page_number == 2
        assert chunks[1].text == "CALL PICK_PART"

        reviews = list(
            session.scalars(
                select(ManualChunkReview)
                .where(ManualChunkReview.manual_id == manual.id)
                .order_by(ManualChunkReview.chunk_index.asc())
            )
        )
        assert len(reviews) == 2
        assert reviews[0].review_status == "reviewed"
        assert reviews[0].selected_reason in {
            "sampled",
            "suspicious_boundary",
            "too_short",
            "too_long",
        }
        assert reviews[0].reviewer_model == "fake-reviewer"

        summary = session.scalar(
            select(ManualReviewSummary).where(
                ManualReviewSummary.manual_id == manual.id
            )
        )
        assert summary is not None
        assert summary.initial_chunk_count == 2
        assert summary.final_chunk_count == 2
        assert summary.reviewed_count == 2
        assert summary.applied_autofixes == 0
        assert summary.estimated_cost_usd >= 0


def test_process_next_pending_manual_marks_failure_when_no_text_is_extracted(
    session_factory,
    db_session: Session,
    monkeypatch,
) -> None:
    manual = create_manual(db_session)

    monkeypatch.setattr(
        "src.jobs.ingestion.extract_pdf_text_by_page", lambda content: ["   ", ""]
    )

    processed = process_next_pending_manual(session_factory, FakeStorageService())

    assert processed is True

    with session_factory() as session:
        refreshed_manual = session.get(Manual, manual.id)
        assert refreshed_manual is not None
        assert refreshed_manual.status == "failed"
        assert refreshed_manual.chunk_count == 0
        assert refreshed_manual.indexed_at is None
        assert refreshed_manual.last_error == "No se pudo extraer texto util del PDF."
        assert (
            session.scalar(
                select(ManualChunk).where(ManualChunk.manual_id == manual.id)
            )
            is None
        )


def test_run_worker_loop_emits_startup_and_heartbeat_when_idle(monkeypatch) -> None:
    log_messages: list[tuple[str, str]] = []
    sleep_calls = {"count": 0}

    def fake_log(scope: str, message: str) -> None:
        log_messages.append((scope, message))

    def fake_sleep(seconds: int) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 1:
            raise RuntimeError("stop-loop")

    monkeypatch.setattr("src.jobs.ingestion.initialize_database", lambda: None)
    monkeypatch.setattr(
        "src.jobs.ingestion.process_next_pending_manual", lambda *args, **kwargs: False
    )
    monkeypatch.setattr("src.jobs.ingestion.log", fake_log)
    monkeypatch.setattr("src.jobs.ingestion.sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        run_worker_loop(
            session_factory=None, storage_service=None, poll_interval_seconds=1
        )  # type: ignore[arg-type]

    assert log_messages == [
        ("worker", "Worker RC7 iniciado. Esperando trabajos de ingesta..."),
    ]


def test_apply_safe_chunk_autofixes_merges_adjacent_chunks(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.jobs.ingestion.settings.semantic_review_autofix_enabled", True
    )
    monkeypatch.setattr(
        "src.jobs.ingestion.settings.semantic_review_merge_boundary_max", 0.6
    )

    chunks = [
        TextChunk(page_number=1, text="Linea 1:"),
        TextChunk(page_number=1, text="continuacion del contenido"),
    ]
    reviews = [
        ChunkReviewResult(
            chunk_index=0,
            page_number=1,
            review_status="reviewed",
            action="merge_with_next",
            boundary_quality_score=0.4,
            reason="corte detectado",
        )
    ]

    fixed_chunks, applied_count = apply_safe_chunk_autofixes(chunks, reviews)

    assert applied_count == 1
    assert len(fixed_chunks) == 1
    assert "Linea 1:" in fixed_chunks[0].text
    assert "continuacion del contenido" in fixed_chunks[0].text
    assert "Auto-fix aplicado: merge_with_next." in (reviews[0].reason or "")


def test_apply_safe_chunk_autofixes_splits_long_chunk(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.jobs.ingestion.settings.semantic_review_autofix_enabled", True
    )
    monkeypatch.setattr(
        "src.jobs.ingestion.settings.semantic_review_split_min_chars", 20
    )
    monkeypatch.setattr(
        "src.jobs.ingestion.settings.semantic_review_split_max_coherence", 0.65
    )

    chunk_text = (
        "Primer bloque tecnico con datos relevantes. "
        "Segundo bloque tecnico separado para simulacion de split."
    )
    chunks = [TextChunk(page_number=2, text=chunk_text)]
    reviews = [
        ChunkReviewResult(
            chunk_index=0,
            page_number=2,
            review_status="reviewed",
            action="split",
            coherence_score=0.5,
            reason="chunk muy denso",
        )
    ]

    fixed_chunks, applied_count = apply_safe_chunk_autofixes(chunks, reviews)

    assert applied_count == 1
    assert len(fixed_chunks) == 2
    assert fixed_chunks[0].text
    assert fixed_chunks[1].text
    assert "Auto-fix aplicado: split." in (reviews[0].reason or "")
