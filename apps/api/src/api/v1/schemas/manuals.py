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
