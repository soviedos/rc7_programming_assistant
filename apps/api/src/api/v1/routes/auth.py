from fastapi import APIRouter, HTTPException, Request, Response, status

from src.api.v1.deps import (
    DbSession,
    clear_session_cookie,
    get_active_role,
    get_current_user,
    set_session_cookie,
)
from src.api.v1.schemas.auth import (
    LoginOptionsResponse,
    LoginRequest,
    LogoutResponse,
    RoleName,
    RoleSwitchRequest,
    SessionResponse,
)
from src.core.config import settings
from src.services.auth.passwords import verify_password
from src.services.auth.users import build_session_response, get_user_by_email

router = APIRouter()


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
