from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ManualChunk(Base):
    __tablename__ = "manual_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manual_id: Mapped[int] = mapped_column(ForeignKey("manuals.id"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
