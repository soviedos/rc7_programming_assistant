"""Shared MinIO storage layer for RC7 Programming Assistant.

Single definition of the manuals bucket client used by ``apps/api`` and
``apps/worker``. Each service keeps its own ``get_manual_storage_service()``
factory to inject its own settings.
"""

from rc7_shared_storage.base import ManualStorageError, ManualStorageService

__all__ = ["ManualStorageError", "ManualStorageService"]
__version__ = "0.1.0"
