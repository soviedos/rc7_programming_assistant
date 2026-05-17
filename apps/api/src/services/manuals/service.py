from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.api.v1.schemas.manuals import ManualResponse
from src.db.models import Manual

_FILENAME_SANITIZER = re.compile(r"[^a-zA-Z0-9._-]+")


def build_storage_key(original_filename: str) -> str:
    normalized_name = Path(original_filename or "manual.pdf").name
    suffix = Path(normalized_name).suffix.lower() or ".pdf"
    stem = _FILENAME_SANITIZER.sub("-", Path(normalized_name).stem).strip("-").lower()
    safe_stem = stem or "manual"
    date_path = datetime.now(UTC).strftime("%Y/%m/%d")
    return f"manuals/{date_path}/{uuid4().hex}-{safe_stem}{suffix}"


def serialize_manual(manual: Manual) -> ManualResponse:
    return ManualResponse(
        id=manual.id,
        title=manual.title,
        original_filename=manual.original_filename,
        storage_key=manual.storage_key,
        content_type=manual.content_type,
        size_bytes=manual.size_bytes,
        sha256=manual.sha256,
        status=manual.status,  # type: ignore[arg-type]
        chunk_count=manual.chunk_count,
        robot_model=manual.robot_model,
        controller_version=manual.controller_version,
        document_language=manual.document_language,  # type: ignore[arg-type]
        categories=manual.categories,  # type: ignore[arg-type]
        notes=manual.notes,
        last_error=manual.last_error,
        uploaded_by_user_id=manual.uploaded_by_user_id,
        uploaded_by_email=manual.uploaded_by_email,
        processing_started_at=manual.processing_started_at,
        indexed_at=manual.indexed_at,
        created_at=manual.created_at,
        updated_at=manual.updated_at,
    )
