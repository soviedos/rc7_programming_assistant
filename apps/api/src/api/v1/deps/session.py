from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.api.v1.schemas.auth import RoleName, SessionResponse
from src.core.config import settings
from src.db.models import User
from src.db.session import get_db_session
from src.services.auth.session_tokens import create_session_token, decode_session_token
from src.services.auth.users import get_user_by_email

DbSession = Annotated[Session, Depends(get_db_session)]


def set_session_cookie(response: Response, session_payload: SessionResponse, user_id: int) -> None:
    token = create_session_token(
        {
            "sub": str(user_id),
            "email": session_payload.email,
            "display_name": session_payload.display_name,
            "role": session_payload.role,
            "available_roles": session_payload.available_roles,
        }
    )

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def get_current_user(request: Request, db_session: DbSession) -> User:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay una sesión activa.",
        )

    try:
        payload = decode_session_token(raw_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida.",
        ) from exc

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no contiene un usuario válido.",
        )

    user = get_user_by_email(db_session, email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario de la sesión ya no está disponible.",
        )

    return user


def get_active_role(request: Request, user: User) -> RoleName:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        return "user"

    try:
        payload = decode_session_token(raw_token)
    except ValueError:
        return "user"

    role = payload.get("role")
    if role in user.roles:
        return role  # type: ignore[return-value]
    return "user"


def get_current_admin_user(request: Request, db_session: DbSession) -> User:
    user = get_current_user(request, db_session)
    active_role = get_active_role(request, user)

    if active_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere una sesion activa con rol de administrador.",
        )

    return user
