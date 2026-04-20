from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ManualStatus = Literal["pending", "processing", "indexed", "failed"]
DocumentLanguage = Literal["es", "en"]


class ManualResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    storage_key: str
    content_type: str
    size_bytes: int
    status: ManualStatus
    chunk_count: int
    robot_model: str | None
    controller_version: str | None
    document_language: DocumentLanguage
    notes: str | None
    last_error: str | None
    uploaded_by_user_id: int
    uploaded_by_email: str
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ManualListResponse(BaseModel):
    items: list[ManualResponse]
    total: int


class ManualUpdateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class ManualReviewSummaryResponse(BaseModel):
    manual_id: int
    initial_chunk_count: int
    final_chunk_count: int
    reviewed_count: int
    skipped_count: int
    error_count: int
    merge_actions: int
    split_actions: int
    keep_actions: int
    regenerate_actions: int
    applied_autofixes: int
    avg_coherence_score: float | None
    avg_completeness_score: float | None
    avg_boundary_quality_score: float | None
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    updated_at: datetime


class ManualReviewSummaryListResponse(BaseModel):
    items: list[ManualReviewSummaryResponse]
    total: int
