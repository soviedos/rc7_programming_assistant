"""Cross-dialect column types shared by the ORM models.

On PostgreSQL these resolve to native ``ARRAY``/``vector`` types; on any other
dialect (e.g. SQLite used by the worker test-suite) they fall back to JSON so
table creation and NULL storage keep working without a pgvector-enabled DB.
"""

import os

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.types import TypeDecorator

# Embedding dimensionality — single source of truth for the shared models.
# Overridable via GEMINI_EMBED_DIM; MUST match the api/worker ``gemini_embed_dim``.
EMBEDDING_DIM = int(os.environ.get("GEMINI_EMBED_DIM", "3072"))


class ArrayOfString(TypeDecorator):
    """Stores list[str] as ARRAY(String) on PostgreSQL, JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(String(32)))
        return dialect.type_descriptor(JSON())


class EmbeddingVector(TypeDecorator):
    """Stores the embedding as pgvector ``vector(N)`` on PostgreSQL, JSON elsewhere.

    The JSON fallback keeps the SQLite-based worker test suite working without a
    pgvector-enabled database; production always runs on PostgreSQL.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(EMBEDDING_DIM))
        return dialect.type_descriptor(JSON())
