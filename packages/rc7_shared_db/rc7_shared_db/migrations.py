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


def ensure_manual_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "manuals" not in set(inspector.get_table_names()):
        return

    existing = {column["name"] for column in inspector.get_columns("manuals")}

    with engine.begin() as connection:
        for column_name, sql_type in _MANUAL_COLUMNS.items():
            if column_name in existing:
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
