from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from src.api.v1.deps import DbSession, get_current_admin_user
from src.api.v1.schemas.admin import (
    AdminStatusResponse,
    AdminUserCreateRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    RolePermissionCreateRequest,
    RolePermissionListResponse,
    RolePermissionResponse,
    RolePermissionUpdateRequest,
    UserRole,
)
from src.db.models import Manual, RolePermission, User
from src.services.auth.passwords import hash_password, validate_password_rules

router = APIRouter()


def normalize_user_role(roles: list[str]) -> UserRole:
    return "admin" if "admin" in roles else "user"


def role_to_roles(role: UserRole) -> list[str]:
    if role == "admin":
        return ["admin", "user"]
    return ["user"]


def serialize_user(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=normalize_user_role(user.roles),
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def serialize_role_permission(permission: RolePermission) -> RolePermissionResponse:
    return RolePermissionResponse(
        id=permission.id,
        key=permission.key,
        name=permission.name,
        description=permission.description,
        admin=permission.admin,
        user=permission.user,
    )


def count_active_admins(db_session: DbSession) -> int:
    active_users = list(
        db_session.scalars(select(User).where(User.is_active.is_(True)))
    )
    return sum(1 for user in active_users if "admin" in user.roles)


def ensure_not_demoting_last_active_admin(
    db_session: DbSession,
    user: User,
    *,
    new_role: UserRole | None = None,
    new_is_active: bool | None = None,
) -> None:
    currently_active_admin = user.is_active and "admin" in user.roles
    next_is_active = user.is_active if new_is_active is None else new_is_active
    next_role = normalize_user_role(user.roles) if new_role is None else new_role
    next_active_admin = next_is_active and next_role == "admin"

    if (
        currently_active_admin
        and not next_active_admin
        and count_active_admins(db_session) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede remover o desactivar al ultimo administrador activo.",
        )


@router.get("/status", response_model=AdminStatusResponse)
async def admin_status(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> AdminStatusResponse:
    manuals_indexed = db_session.scalar(
        select(func.count(Manual.id)).where(Manual.status == "indexed")
    )
    active_users = db_session.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    pending_jobs = db_session.scalar(
        select(func.count(Manual.id)).where(
            Manual.status.in_(["pending", "processing"])
        )
    )

    return AdminStatusResponse(
        manuals_indexed=manuals_indexed or 0,
        active_users=active_users or 0,
        pending_jobs=pending_jobs or 0,
    )


@router.get("/roles/permissions", response_model=RolePermissionListResponse)
async def get_role_permissions(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> RolePermissionListResponse:
    permissions = list(
        db_session.scalars(
            select(RolePermission).order_by(
                RolePermission.key.asc(), RolePermission.id.asc()
            )
        )
    )
    return RolePermissionListResponse(
        items=[serialize_role_permission(permission) for permission in permissions]
    )


@router.post(
    "/roles/permissions",
    response_model=RolePermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_permission(
    payload: RolePermissionCreateRequest,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> RolePermissionResponse:
    normalized_key = payload.key.strip().lower()
    existing = db_session.scalar(
        select(RolePermission).where(RolePermission.key == normalized_key)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un permiso con esa clave.",
        )

    permission = RolePermission(
        key=normalized_key,
        name=payload.name.strip(),
        description=payload.description.strip(),
        admin=payload.admin,
        user=payload.user,
    )
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return serialize_role_permission(permission)


@router.put("/roles/permissions/{permission_id}", response_model=RolePermissionResponse)
async def update_role_permission(
    permission_id: int,
    payload: RolePermissionUpdateRequest,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> RolePermissionResponse:
    permission = db_session.get(RolePermission, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el permiso solicitado.",
        )

    permission.name = payload.name.strip()
    permission.description = payload.description.strip()
    permission.admin = payload.admin
    permission.user = payload.user

    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return serialize_role_permission(permission)


@router.delete(
    "/roles/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_role_permission(
    permission_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> None:
    permission = db_session.get(RolePermission, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el permiso solicitado.",
        )

    db_session.delete(permission)
    db_session.commit()


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> AdminUserListResponse:
    users = list(
        db_session.scalars(
            select(User).order_by(User.created_at.desc(), User.id.desc())
        )
    )
    return AdminUserListResponse(
        items=[serialize_user(user) for user in users], total=len(users)
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: int,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> AdminUserResponse:
    user = db_session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el usuario solicitado.",
        )
    return serialize_user(user)


@router.post(
    "/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    payload: AdminUserCreateRequest,
    db_session: DbSession,
    _: User = Depends(get_current_admin_user),
) -> AdminUserResponse:
    normalized_email = payload.email.strip().lower()
    existing_user = db_session.scalar(
        select(User).where(User.email == normalized_email)
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo.",
        )

    password_rules_error = validate_password_rules(payload.password)
    if password_rules_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=password_rules_error,
        )

    user = User(
        email=normalized_email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        roles=role_to_roles(payload.role),
        profile_settings={},
        is_active=payload.is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return serialize_user(user)


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    db_session: DbSession,
    current_admin: User = Depends(get_current_admin_user),
) -> AdminUserResponse:
    user = db_session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el usuario solicitado.",
        )

    if current_admin.id == user.id and (
        payload.role != "admin" or payload.is_active is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes quitarte el rol admin ni desactivar tu propio usuario.",
        )

    ensure_not_demoting_last_active_admin(
        db_session,
        user,
        new_role=payload.role,
        new_is_active=payload.is_active,
    )

    if payload.password is not None:
        password_rules_error = validate_password_rules(payload.password)
        if password_rules_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=password_rules_error,
            )
        user.password_hash = hash_password(payload.password)

    user.display_name = payload.display_name.strip()
    user.roles = role_to_roles(payload.role)
    user.is_active = payload.is_active

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return serialize_user(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db_session: DbSession,
    current_admin: User = Depends(get_current_admin_user),
) -> None:
    user = db_session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el usuario solicitado.",
        )

    if current_admin.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario.",
        )

    ensure_not_demoting_last_active_admin(
        db_session, user, new_is_active=False, new_role="user"
    )

    db_session.delete(user)
    db_session.commit()
