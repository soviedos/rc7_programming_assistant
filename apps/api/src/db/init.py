from sqlalchemy import inspect, select, text

from src.core.config import settings
from src.db.base import Base
from src.db.models import User
from src.db.session import SessionLocal, engine
from src.services.auth.passwords import hash_password


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()
    ensure_manual_columns()
    seed_bootstrap_admin()


def ensure_user_columns() -> None:
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "profile_settings" in user_columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN IF NOT EXISTS profile_settings JSON "
                    "DEFAULT '{}'::json NOT NULL"
                )
            )
        else:
            connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN profile_settings JSON DEFAULT '{}' NOT NULL"
                )
            )


def ensure_manual_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "manuals" not in table_names:
        return

    manual_columns = {column["name"] for column in inspector.get_columns("manuals")}
    missing_columns = {
        "chunk_count": "INTEGER DEFAULT 0 NOT NULL",
        "last_error": "TEXT",
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


def seed_bootstrap_admin() -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return

    normalized_email = settings.bootstrap_admin_email.strip().lower()

    with SessionLocal() as session:
        existing_user = session.scalar(
            select(User).where(User.email == normalized_email)
        )
        if existing_user:
            return

        admin_user = User(
            email=normalized_email,
            display_name=settings.bootstrap_admin_name.strip() or "Administrador RC7",
            password_hash=hash_password(settings.bootstrap_admin_password),
            roles=["admin", "user"],
            profile_settings={},
            is_active=True,
        )
        session.add(admin_user)
        session.commit()
