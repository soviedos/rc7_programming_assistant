from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.types import TypeDecorator

# Embedding dimensionality — MUST match _OUTPUT_DIMENSIONALITY in the worker's
# embeddings service and _EMBED_DIM in the API chat service.
EMBEDDING_DIM = 3072


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
