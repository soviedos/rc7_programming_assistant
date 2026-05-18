from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.deps import DbSession, get_current_admin_user
from src.api.v1.schemas.audit import AuditLogEntry, AuditLogResponse
from src.db.models import User
from src.services.audit_service import get_audit_logs

router = APIRouter()


def _serialize(row) -> AuditLogEntry:
    return AuditLogEntry(
        id=row.id,
        event_type=row.event_type,
        actor_id=row.actor_id,
        actor_email=row.actor_email,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        description=row.description,
        event_metadata=row.event_metadata,
        ip_address=row.ip_address,
        created_at=row.created_at,
    )


@router.get("", response_model=AuditLogResponse)
def list_audit_logs(
    db: DbSession,
    _: User = Depends(get_current_admin_user),
    event_type: str | None = Query(default=None),
    actor_id: int | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AuditLogResponse:
    items, total = get_audit_logs(
        db,
        event_type=event_type,
        actor_id=actor_id,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    pages = max(1, math.ceil(total / page_size))
    return AuditLogResponse(
        items=[_serialize(r) for r in items],
        total=total,
        page=page,
        pages=pages,
    )


@router.get("/{log_id}", response_model=AuditLogEntry)
def get_audit_log(
    log_id: str,
    db: DbSession,
    _: User = Depends(get_current_admin_user),
) -> AuditLogEntry:
    from sqlalchemy import select
    from src.db.models.audit import AuditLog

    row = db.scalar(select(AuditLog).where(AuditLog.id == log_id))
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento de auditoría no encontrado.",
        )
    return _serialize(row)
