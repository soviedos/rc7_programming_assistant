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
    RoleSwitchRequest,
    SessionResponse,
)
from src.services.audit_service import log_event
from src.services.auth.passwords import verify_password
from src.services.auth.users import build_session_response, get_user_by_email

router = APIRouter()


@router.get("/providers", response_model=LoginOptionsResponse)
def auth_providers() -> LoginOptionsResponse:
    return LoginOptionsResponse(
        providers=["google"],
        note="El login con Google se implementara en una siguiente iteracion.",
    )


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db_session: DbSession,
) -> SessionResponse:
    user = get_user_by_email(db_session, payload.email)

    if (
        not user
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        log_event(
            db_session,
            "AUTH_FAILED",
            f"Intento de login fallido para {payload.email}",
            actor_email=payload.email,
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas.",
        )

    session_response = build_session_response(
        user,
        "admin" if "admin" in user.roles else "user",
    )
    set_session_cookie(response, session_response, user.id)
    log_event(
        db_session,
        "AUTH_LOGIN",
        f"Inicio de sesion exitoso para {user.email}",
        actor_id=user.id,
        actor_email=user.email,
        ip_address=request.client.host if request.client else None,
    )
    return session_response


@router.get("/me", response_model=SessionResponse)
def me(request: Request, db_session: DbSession) -> SessionResponse:
    user = get_current_user(request, db_session)
    active_role = get_active_role(request, user)
    return build_session_response(user, active_role)


@router.post("/switch-role", response_model=SessionResponse)
def switch_role(
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
def logout(
    request: Request, response: Response, db_session: DbSession
) -> LogoutResponse:
    try:
        user = get_current_user(request, db_session)
        log_event(
            db_session,
            "AUTH_LOGOUT",
            f"Cierre de sesion para {user.email}",
            actor_id=user.id,
            actor_email=user.email,
            ip_address=request.client.host if request.client else None,
        )
    except Exception:
        pass
    clear_session_cookie(response)
    return LogoutResponse(success=True)
