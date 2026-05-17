from sqlalchemy import inspect, select, text

from src.core.config import settings
from src.db.base import Base
from src.db.models import ChatHistory, RolePermission, User
from src.db.session import SessionLocal, engine
from src.services.auth.passwords import hash_password


DEFAULT_ROLE_PERMISSIONS = [
    {
        "key": "manuals",
        "name": "Manuales",
        "description": "Ver, subir y gestionar la base documental.",
        "admin": True,
        "user": False,
    },
    {
        "key": "users",
        "name": "Usuarios",
        "description": "CRUD completo de cuentas y asignacion de rol.",
        "admin": True,
        "user": False,
    },
    {
        "key": "chat",
        "name": "Chat",
        "description": "Usar el asistente para consultas tecnicas.",
        "admin": True,
        "user": True,
    },
    {
        "key": "profile",
        "name": "Perfil y configuracion",
        "description": "Actualizar perfil, idioma y contrasena.",
        "admin": True,
        "user": True,
    },
    {
        "key": "role-switch",
        "name": "Cambio de rol",
        "description": "Alternar entre vista admin y vista usuario cuando aplique.",
        "admin": True,
        "user": True,
    },
]


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()
    ensure_manual_columns()
    ensure_chunk_embedding_column()
    ensure_chat_history_table()
    seed_bootstrap_admin()
    seed_role_permissions()


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
        "processing_started_at": "TIMESTAMP",
        "indexed_at": "TIMESTAMP",
        "sha256": "VARCHAR(64)",
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


def ensure_chunk_embedding_column() -> None:
    """Add embedding REAL[] column to manual_chunks if it does not exist yet."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "manual_chunks" not in table_names:
        return

    chunk_columns = {
        column["name"] for column in inspector.get_columns("manual_chunks")
    }
    if "embedding" in chunk_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE manual_chunks ADD COLUMN IF NOT EXISTS embedding REAL[]")
        )


def ensure_chat_history_table() -> None:
    """Create the chat_history table if it does not exist yet."""
    inspector = inspect(engine)
    if "chat_history" in set(inspector.get_table_names()):
        return

    ChatHistory.__table__.create(bind=engine)


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


def seed_role_permissions() -> None:
    with SessionLocal() as session:
        existing_keys = {
            key for key in session.scalars(select(RolePermission.key)).all()
        }

        for permission in DEFAULT_ROLE_PERMISSIONS:
            if permission["key"] in existing_keys:
                continue

            session.add(
                RolePermission(
                    key=permission["key"],
                    name=permission["name"],
                    description=permission["description"],
                    admin=permission["admin"],
                    user=permission["user"],
                )
            )

        session.commit()
