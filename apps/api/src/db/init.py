from sqlalchemy import select

from src.core.config import settings
from src.db.base import Base
from src.db.models import User
from src.db.session import SessionLocal, engine
from src.services.auth.passwords import hash_password


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    seed_bootstrap_admin()


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
            is_active=True,
        )
        session.add(admin_user)
        session.commit()
