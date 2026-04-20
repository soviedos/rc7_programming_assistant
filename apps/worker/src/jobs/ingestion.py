from __future__ import annotations

from datetime import UTC, datetime
from time import sleep

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from src.chunking.text import TextChunk, build_text_chunks
from src.core.config import settings
from src.db.models import Manual, ManualChunk
from src.db.session import SessionLocal, initialize_database
from src.parsers.pdf import extract_pdf_text_by_page
from src.services.storage import ManualStorageService, get_manual_storage_service
from src.utils.logging import log


def claim_next_pending_manual(session: Session) -> Manual | None:
    statement = select(Manual).where(Manual.status == "pending").order_by(Manual.created_at.asc(), Manual.id.asc())

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
) -> None:
    session.execute(delete(ManualChunk).where(ManualChunk.manual_id == manual.id))

    for chunk_index, chunk in enumerate(chunks):
        session.add(
            ManualChunk(
                manual_id=manual.id,
                chunk_index=chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
            )
        )

    manual.status = "indexed"
    manual.chunk_count = len(chunks)
    manual.last_error = None
    manual.indexed_at = datetime.now(UTC)
    session.add(manual)
    session.commit()


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
) -> bool:
    storage = storage_service or get_manual_storage_service()

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

            index_manual_chunks(session, manual, chunks)
            log(
                "worker",
                f"Manual #{manual.id} indexado correctamente con {len(chunks)} chunks.",
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
