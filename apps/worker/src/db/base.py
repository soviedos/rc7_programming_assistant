"""Re-export the shared declarative Base.

The single ``Base`` (and its MetaData) lives in the ``rc7_shared_db`` package so
the shared models register on the same metadata as the rest of the worker.
"""

from rc7_shared_db.base import Base

__all__ = ["Base"]
