from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v1.schemas.auth import RoleName, SessionResponse
from src.db.models import User


def normalize_roles(roles: list[str]) -> list[RoleName]:
    normalized = [role for role in roles if role in {"admin", "user"}]
    if not normalized:
        return ["user"]
    return normalized  # type: ignore[return-value]


def get_user_by_email(session: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    return session.scalar(select(User).where(User.email == normalized_email))


def build_session_response(user: User, active_role: RoleName) -> SessionResponse:
    available_roles = normalize_roles(user.roles)
    role = active_role if active_role in available_roles else available_roles[0]

    return SessionResponse(
        email=user.email,
        display_name=user.display_name,
        role=role,
        available_roles=available_roles,
        redirect_path="/admin" if role == "admin" else "/app",
    )
