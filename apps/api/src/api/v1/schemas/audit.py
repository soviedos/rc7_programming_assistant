from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    id: str
    event_type: str
    actor_id: int | None
    actor_email: str | None
    resource_type: str | None
    resource_id: str | None
    description: str
    event_metadata: dict | None
    ip_address: str | None
    created_at: datetime


class AuditLogResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    pages: int
