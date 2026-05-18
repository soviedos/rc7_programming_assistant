from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.deps import DbSession, get_current_admin_user
from src.api.v1.schemas.settings import (
    SettingRead,
    SettingsBulkUpdate,
    SettingUpdate,
    SettingsResponse,
)
from src.db.models import User
from src.services.settings import service as settings_service

router = APIRouter()


def _serialize(row) -> SettingRead:
    return SettingRead(
        id=row.id,
        key=row.key,
        value=row.value,
        description=row.description,
        updated_at=row.updated_at,
    )


@router.get("", response_model=SettingsResponse)
def list_settings(
    db: DbSession,
    _: User = Depends(get_current_admin_user),
) -> SettingsResponse:
    rows = settings_service.get_all_settings(db)
    return SettingsResponse(items=[_serialize(r) for r in rows])


@router.get("/{key}", response_model=SettingRead)
def get_setting(
    key: str,
    db: DbSession,
    _: User = Depends(get_current_admin_user),
) -> SettingRead:
    row = settings_service.get_setting(db, key)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración '{key}' no encontrada.",
        )
    return _serialize(row)


@router.put("/{key}", response_model=SettingRead)
def update_setting(
    key: str,
    body: SettingUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_admin_user),
) -> SettingRead:
    row = settings_service.update_setting(
        db, key, body.value, updated_by=current_user.id
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración '{key}' no encontrada.",
        )
    return _serialize(row)


@router.post("/reset", response_model=SettingsResponse)
def reset_settings(
    db: DbSession,
    _: User = Depends(get_current_admin_user),
) -> SettingsResponse:
    settings_service.reset_to_defaults(db)
    rows = settings_service.get_all_settings(db)
    return SettingsResponse(items=[_serialize(r) for r in rows])
