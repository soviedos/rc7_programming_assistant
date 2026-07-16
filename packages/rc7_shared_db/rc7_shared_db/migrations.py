"""Idempotent schema migrations for the tables shared by api and worker.

Both services run these on startup, so they must agree on the schema. Keeping a
copy per service is how ``manuals.sha256`` ended up being added by the API and
not by the worker.
"""

from sqlalchemy import Engine, inspect, text

# Columns added to ``manuals`` after the table's first release. create_all() only
# creates missing tables, never missing columns, so existing installs need this.
_MANUAL_COLUMNS: dict[str, str] = {
    "chunk_count": "INTEGER DEFAULT 0 NOT NULL",
    "last_error": "TEXT",
    "processing_started_at": "TIMESTAMP",
    "indexed_at": "TIMESTAMP",
    "sha256": "VARCHAR(64)",
}


# Columnas añadidas a ``manual_chunks`` tras su primera versión.
_MANUAL_CHUNK_COLUMNS: dict[str, str] = {
    "section_title": "VARCHAR(500)",
}


def _add_missing_columns(engine: Engine, table: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in set(inspector.get_table_names()):
        return

    existing = {column["name"] for column in inspector.get_columns(table)}

    with engine.begin() as connection:
        for column_name, sql_type in columns.items():
            if column_name in existing:
                continue

            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_name} {sql_type}"
                    )
                )
            else:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column_name} {sql_type}")
                )


def ensure_manual_columns(engine: Engine) -> None:
    _add_missing_columns(engine, "manuals", _MANUAL_COLUMNS)
    _add_missing_columns(engine, "manual_chunks", _MANUAL_CHUNK_COLUMNS)
