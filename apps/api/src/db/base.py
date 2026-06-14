"""Re-export the shared declarative Base.

The single ``Base`` (and its MetaData) lives in the ``rc7_shared_db`` package so
the shared models and the API-specific models register on the same metadata.
"""

from rc7_shared_db.base import Base

__all__ = ["Base"]
