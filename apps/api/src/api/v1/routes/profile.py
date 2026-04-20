from fastapi import APIRouter, HTTPException, Request, Response, status

from src.api.v1.deps import DbSession, get_active_role, get_current_user, set_session_cookie
from src.api.v1.schemas.profile import (
    ChangePasswordRequest,
    ProfileActionResponse,
    ProfileResponse,
    ProfileSettings,
    UpdateProfileRequest,
)
from src.services.auth.passwords import (
    hash_password,
    validate_password_rules,
    verify_password,
)
from src.services.auth.users import build_session_response

router = APIRouter()


def normalize_profile_settings(raw_settings: dict[str, str] | None) -> ProfileSettings:
    return ProfileSettings.model_validate(raw_settings or {})


@router.get("", response_model=ProfileResponse)
async def get_profile(request: Request, db_session: DbSession) -> ProfileResponse:
    user = get_current_user(request, db_session)
    return ProfileResponse(
        email=user.email,
        display_name=user.display_name,
        settings=normalize_profile_settings(user.profile_settings),
    )


@router.put("", response_model=ProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    request: Request,
    response: Response,
    db_session: DbSession,
) -> ProfileResponse:
    user = get_current_user(request, db_session)
    user.display_name = payload.display_name.strip()
    user.profile_settings = payload.settings.model_dump()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    active_role = get_active_role(request, user)
    session_response = build_session_response(user, active_role)
    set_session_cookie(response, session_response, user.id)

    return ProfileResponse(
        email=user.email,
        display_name=user.display_name,
        settings=normalize_profile_settings(user.profile_settings),
    )


@router.post("/password", response_model=ProfileActionResponse)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db_session: DbSession,
) -> ProfileActionResponse:
    user = get_current_user(request, db_session)

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual.",
        )

    password_rules_error = validate_password_rules(payload.new_password)
    if password_rules_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=password_rules_error,
        )

    user.password_hash = hash_password(payload.new_password)
    db_session.add(user)
    db_session.commit()

    return ProfileActionResponse(
        success=True,
        message="La contraseña se actualizó correctamente.",
    )
