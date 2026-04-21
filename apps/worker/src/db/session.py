from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.db.base import Base

engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_manual_columns()


def ensure_manual_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "manuals" not in table_names:
        return

    manual_columns = {column["name"] for column in inspector.get_columns("manuals")}
    missing_columns = {
        "chunk_count": "INTEGER DEFAULT 0 NOT NULL",
        "last_error": "TEXT",
        "processing_started_at": "TIMESTAMP",
        "indexed_at": "TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, sql_type in missing_columns.items():
            if column_name in manual_columns:
                continue

            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        f"ALTER TABLE manuals ADD COLUMN IF NOT EXISTS {column_name} {sql_type}"
                    )
                )
            else:
                connection.execute(
                    text(f"ALTER TABLE manuals ADD COLUMN {column_name} {sql_type}")
                )
