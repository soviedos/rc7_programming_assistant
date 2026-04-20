import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Manual, ManualChunk
from src.jobs.ingestion import process_next_pending_manual, run_worker_loop


class FakeStorageService:
    def __init__(self, content: bytes = b"%PDF-1.4 fake") -> None:
        self.content = content
        self.keys: list[str] = []

    def download_manual(self, storage_key: str) -> bytes:
        self.keys.append(storage_key)
        return self.content


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

    processed = process_next_pending_manual(session_factory, storage)

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


def test_process_next_pending_manual_marks_failure_when_no_text_is_extracted(
    session_factory,
    db_session: Session,
    monkeypatch,
) -> None:
    manual = create_manual(db_session)

    monkeypatch.setattr("src.jobs.ingestion.extract_pdf_text_by_page", lambda content: ["   ", ""])

    processed = process_next_pending_manual(session_factory, FakeStorageService())

    assert processed is True

    with session_factory() as session:
        refreshed_manual = session.get(Manual, manual.id)
        assert refreshed_manual is not None
        assert refreshed_manual.status == "failed"
        assert refreshed_manual.chunk_count == 0
        assert refreshed_manual.indexed_at is None
        assert refreshed_manual.last_error == "No se pudo extraer texto util del PDF."
        assert session.scalar(select(ManualChunk).where(ManualChunk.manual_id == manual.id)) is None


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
    monkeypatch.setattr("src.jobs.ingestion.process_next_pending_manual", lambda *args, **kwargs: False)
    monkeypatch.setattr("src.jobs.ingestion.log", fake_log)
    monkeypatch.setattr("src.jobs.ingestion.sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        run_worker_loop(session_factory=None, storage_service=None, poll_interval_seconds=1)  # type: ignore[arg-type]

    assert log_messages == [
        ("worker", "Worker RC7 iniciado. Esperando trabajos de ingesta..."),
    ]
