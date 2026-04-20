from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ManualReviewSummary(Base):
    __tablename__ = "manual_review_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manual_id: Mapped[int] = mapped_column(
        ForeignKey("manuals.id"),
        unique=True,
        index=True,
        nullable=False,
    )
    initial_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    final_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    merge_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    split_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    keep_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regenerate_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applied_autofixes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_coherence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_boundary_quality_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    estimated_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    estimated_output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    estimated_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
