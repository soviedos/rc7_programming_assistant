from sqlalchemy import inspect, select, text

from src.core.config import settings
from src.db.base import Base
from src.db.models import AuditLog, ChatHistory, RolePermission, SystemSetting, User
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


# Embedding dimensionality — single-sourced from config (settings.gemini_embed_dim),
# identical across the chat service, the worker and the ManualChunk Vector(N).
EMBEDDING_DIM = settings.gemini_embed_dim
_EMBEDDING_INDEX = "manual_chunks_embedding_hnsw"
# Legacy index name from a previous migration — dropped if present.
_EMBEDDING_INDEX_LEGACY = "manual_chunks_embedding_hnsw_idx"


def initialize_database() -> None:
    # The pgvector extension must exist before create_all emits the vector column.
    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()
    ensure_manual_columns()
    ensure_chunk_embedding_column()
    ensure_chat_history_table()
    ensure_settings_table()
    ensure_audit_log_table()
    seed_bootstrap_admin()
    seed_role_permissions()
    seed_default_settings()


def ensure_vector_extension() -> None:
    """Enable the pgvector extension (no-op on non-PostgreSQL backends)."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


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
    """Ensure manual_chunks.embedding is a pgvector ``vector(EMBEDDING_DIM)`` column.

    Idempotent migration that also upgrades existing installations: a legacy
    ``REAL[]`` (or wrong-dimension) column is dropped and recreated as
    ``vector(EMBEDDING_DIM)``. This is safe because embeddings are repopulated by
    re-embedding rather than migrated in place. Finally an HNSW cosine index is
    created. Because pgvector caps HNSW on ``vector`` at 2000 dimensions, the
    index is built on a ``halfvec`` cast (supports up to 4000 dims).
    """
    inspector = inspect(engine)
    if "manual_chunks" not in set(inspector.get_table_names()):
        return

    if engine.dialect.name != "postgresql":
        chunk_columns = {
            column["name"] for column in inspector.get_columns("manual_chunks")
        }
        if "embedding" not in chunk_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE manual_chunks ADD COLUMN embedding JSON")
                )
        return

    target_type = f"vector({EMBEDDING_DIM})"
    with engine.begin() as connection:
        current_type = connection.execute(
            text(
                "SELECT format_type(a.atttypid, a.atttypmod) "
                "FROM pg_attribute a "
                "WHERE a.attrelid = 'manual_chunks'::regclass "
                "AND a.attname = 'embedding' AND NOT a.attisdropped"
            )
        ).scalar()

        if current_type != target_type:
            # Drop a legacy/wrong-typed column and its dependent indexes, then
            # recreate at the correct vector dimension (repopulated on re-embed).
            connection.execute(text(f"DROP INDEX IF EXISTS {_EMBEDDING_INDEX}"))
            connection.execute(text(f"DROP INDEX IF EXISTS {_EMBEDDING_INDEX_LEGACY}"))
            connection.execute(
                text("ALTER TABLE manual_chunks DROP COLUMN IF EXISTS embedding")
            )
            connection.execute(
                text(
                    f"ALTER TABLE manual_chunks ADD COLUMN embedding {target_type}"
                )
            )

        # Drop the legacy-named index so only the canonical one remains.
        connection.execute(text(f"DROP INDEX IF EXISTS {_EMBEDDING_INDEX_LEGACY}"))
        # HNSW cosine index. pgvector caps HNSW on `vector` at 2000 dims, so for
        # 3072-dim embeddings the index is built on a halfvec cast (up to 4000
        # dims) with halfvec_cosine_ops; queries cast both sides to halfvec so
        # the `<=>` ORDER BY uses this index.
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {_EMBEDDING_INDEX} "
                "ON manual_chunks "
                f"USING hnsw ((embedding::halfvec({EMBEDDING_DIM})) halfvec_cosine_ops)"
            )
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


def ensure_settings_table() -> None:
    """Create the system_settings table if it does not exist yet."""
    inspector = inspect(engine)
    if "system_settings" in set(inspector.get_table_names()):
        return
    SystemSetting.__table__.create(bind=engine)


def ensure_audit_log_table() -> None:
    """Create the audit_log table if it does not exist yet."""
    inspector = inspect(engine)
    if "audit_log" in set(inspector.get_table_names()):
        return
    AuditLog.__table__.create(bind=engine)


def seed_default_settings() -> None:
    """Insert default system settings for any keys not yet present."""
    from src.services.settings.service import (
        seed_if_empty,
    )  # local import avoids circularity

    with SessionLocal() as session:
        seed_if_empty(session)
