from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from rc7_shared_db.base import Base
from rc7_shared_db.types import EMBEDDING_DIM, EmbeddingVector

__all__ = ["EMBEDDING_DIM", "ManualChunk"]


class ManualChunk(Base):
    __tablename__ = "manual_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manual_id: Mapped[int] = mapped_column(
        ForeignKey("manuals.id"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Sección del manual (outline del PDF). Nullable: los PDFs sin outline y los
    # chunks anteriores a esta columna no la tienen.
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingVector(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
