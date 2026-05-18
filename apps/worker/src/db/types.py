from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.types import TypeDecorator


class ArrayOfString(TypeDecorator):
    """Stores list[str] as ARRAY(String) on PostgreSQL, JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(String(32)))
        return dialect.type_descriptor(JSON())


class ArrayOfFloat(TypeDecorator):
    """Stores list[float] as ARRAY(REAL) on PostgreSQL, JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(REAL))
        return dialect.type_descriptor(JSON())
