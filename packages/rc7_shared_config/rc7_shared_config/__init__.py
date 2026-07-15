"""Shared configuration layer for RC7 Programming Assistant.

Single source of truth for the settings that ``apps/api`` and ``apps/worker`` both
need — Postgres, MinIO and Gemini — plus the production secret validation. Each
service subclasses ``SharedSettings`` and declares only its own fields.
"""

from rc7_shared_config.base import (
    PLACEHOLDER,
    WEAK_PASSWORDS,
    SharedSettings,
)

__all__ = ["PLACEHOLDER", "WEAK_PASSWORDS", "SharedSettings"]
__version__ = "0.1.0"
