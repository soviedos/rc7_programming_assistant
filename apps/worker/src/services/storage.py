from __future__ import annotations

from rc7_shared_storage import ManualStorageError, ManualStorageService

from src.core.config import settings

__all__ = ["ManualStorageError", "ManualStorageService", "get_manual_storage_service"]


def get_manual_storage_service() -> ManualStorageService:
    return ManualStorageService(settings)
