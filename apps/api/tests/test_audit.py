import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User
from src.db.models.audit import AuditLog
from src.services.audit_service import log_event, get_audit_logs
from tests.helpers import create_user, login


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_entry(db: Session, event_type: str = "AUTH_LOGIN") -> AuditLog:
    """Insert a single AuditLog row directly for test setup."""
    entry = AuditLog(
        id=str(uuid.uuid4()),
        event_type=event_type,
        description=f"Test event: {event_type}",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ──────────────────────────────────────────────────────────────────────────────
# Service-level tests
# ──────────────────────────────────────────────────────────────────────────────


def test_log_event_creates_record(db_session: Session) -> None:
    log_event(
        db_session,
        "AUTH_LOGIN",
        "Login exitoso",
        actor_id=1,
        actor_email="admin@test.com",
        ip_address="127.0.0.1",
    )
    rows = list(
        db_session.scalars(select(AuditLog).where(AuditLog.event_type == "AUTH_LOGIN"))
    )
    assert len(rows) == 1
    assert rows[0].actor_email == "admin@test.com"
    assert rows[0].ip_address == "127.0.0.1"


def test_log_event_never_raises(db_session: Session) -> None:
    """log_event must swallow exceptions gracefully."""
    # Force an error by closing the session first
    db_session.close()
    # Should not raise
    log_event(db_session, "SYSTEM_ERROR", "Broken session test")


def test_log_event_stores_metadata(db_session: Session) -> None:
    log_event(
        db_session,
        "CHAT_QUERY",
        "Consulta procesada",
        metadata={"robot_type": "RC7", "references_count": 3},
    )
    row = db_session.scalar(select(AuditLog).where(AuditLog.event_type == "CHAT_QUERY"))
    assert row is not None
    assert row.event_metadata == {"robot_type": "RC7", "references_count": 3}


def test_get_audit_logs_pagination(db_session: Session) -> None:
    for i in range(5):
        _make_entry(db_session, "SETTING_UPDATED")

    items, total = get_audit_logs(db_session, page=1, page_size=2)
    assert total == 5
    assert len(items) == 2


def test_get_audit_logs_filter_by_event_type(db_session: Session) -> None:
    _make_entry(db_session, "AUTH_LOGIN")
    _make_entry(db_session, "CHAT_QUERY")
    _make_entry(db_session, "AUTH_LOGIN")

    items, total = get_audit_logs(db_session, event_type="AUTH_LOGIN")
    assert total == 2
    assert all(i.event_type == "AUTH_LOGIN" for i in items)


# ──────────────────────────────────────────────────────────────────────────────
# Route-level tests (HTTP)
# ──────────────────────────────────────────────────────────────────────────────


def test_audit_list_requires_admin(client: TestClient, db_session: Session) -> None:
    create_user(db_session, email="user@test.com", password="secret", roles=["user"])
    login(client, "user@test.com", "secret")

    response = client.get("/api/v1/admin/audit")
    assert response.status_code == 403


def test_audit_list_returns_paginated_results(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")

    for _ in range(3):
        _make_entry(db_session, "AUTH_LOGIN")

    response = client.get("/api/v1/admin/audit?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert "pages" in data


def test_audit_get_single_entry(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")

    entry = _make_entry(db_session, "SETTING_UPDATED")

    response = client.get(f"/api/v1/admin/audit/{entry.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entry.id
    assert data["event_type"] == "SETTING_UPDATED"


def test_audit_get_nonexistent_entry(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")

    response = client.get("/api/v1/admin/audit/nonexistent-uuid")
    assert response.status_code == 404


def test_audit_filter_by_event_type_via_api(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")

    _make_entry(db_session, "AUTH_LOGIN")
    _make_entry(db_session, "CHAT_QUERY")

    response = client.get("/api/v1/admin/audit?event_type=AUTH_LOGIN")
    assert response.status_code == 200
    data = response.json()
    assert all(item["event_type"] == "AUTH_LOGIN" for item in data["items"])
