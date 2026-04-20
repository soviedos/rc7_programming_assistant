from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Manual(Base):
    __tablename__ = "manuals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    robot_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    document_language: Mapped[str] = mapped_column(String(8), default="es")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(Integer, index=True)
    uploaded_by_email: Mapped[str] = mapped_column(String(320))
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
