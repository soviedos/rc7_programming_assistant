from __future__ import annotations

import sys
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models.audit import AuditLog


def log_event(
    db: Session,
    event_type: str,
    description: str,
    *,
    actor_id: int | None = None,
    actor_email: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit event. Never raises — failures are logged to stderr."""
    try:
        entry = AuditLog(
            id=str(uuid.uuid4()),
            event_type=event_type,
            actor_id=actor_id,
            actor_email=actor_email,
            resource_type=resource_type,
            resource_id=None if resource_id is None else str(resource_id),
            description=description,
            event_metadata=metadata,
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        print(f"[audit] ERROR logging event {event_type}: {exc}", file=sys.stderr)


def get_audit_logs(
    db: Session,
    *,
    event_type: str | None = None,
    actor_id: int | None = None,
    resource_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    """Return (items, total) for the given filters and page."""
    query = select(AuditLog)

    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if actor_id is not None:
        query = query.where(AuditLog.actor_id == actor_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
        )
    )
    return items, total
