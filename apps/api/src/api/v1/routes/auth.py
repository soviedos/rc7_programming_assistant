from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.api.v1.schemas.auth import (
    LoginOptionsResponse,
    LoginRequest,
    LogoutResponse,
    RoleName,
    RoleSwitchRequest,
    SessionResponse,
)
from src.core.config import settings
from src.db.models import User
from src.db.session import get_db_session
from src.services.auth.passwords import verify_password
from src.services.auth.session_tokens import (
    create_session_token,
    decode_session_token,
)
from src.services.auth.users import build_session_response, get_user_by_email

router = APIRouter()

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


@router.get("/providers", response_model=LoginOptionsResponse)
async def auth_providers() -> LoginOptionsResponse:
    return LoginOptionsResponse(
        providers=["google"],
        note="El login con Google se implementara en una siguiente iteracion.",
    )


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db_session: DbSession,
) -> SessionResponse:
    user = get_user_by_email(db_session, payload.email)

    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas.",
        )

    session_response = build_session_response(
        user,
        "admin" if "admin" in user.roles else "user",
    )
    set_session_cookie(response, session_response, user.id)
    return session_response


@router.get("/me", response_model=SessionResponse)
async def me(request: Request, db_session: DbSession) -> SessionResponse:
    user = get_current_user(request, db_session)
    active_role = get_active_role(request, user)
    return build_session_response(user, active_role)


@router.post("/switch-role", response_model=SessionResponse)
async def switch_role(
    payload: RoleSwitchRequest,
    request: Request,
    response: Response,
    db_session: DbSession,
) -> SessionResponse:
    user = get_current_user(request, db_session)
    available_roles = set(user.roles)

    if payload.role not in available_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese usuario no tiene permiso para usar ese rol.",
        )

    session_response = build_session_response(user, payload.role)
    set_session_cookie(response, session_response, user.id)
    return session_response


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    clear_session_cookie(response)
    return LogoutResponse(success=True)
