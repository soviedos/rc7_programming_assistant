from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import Manual, User
from src.services.auth.passwords import hash_password


def test_root_route(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "RC7 Programming Assistant API",
        "docs": "/docs",
    }


def test_health_route(client: TestClient) -> None:
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_status_route(client: TestClient, db_session: Session) -> None:
    active_user = User(
        email="activo@ucenfotec.ac.cr",
        display_name="Activo",
        password_hash=hash_password("1234ABC"),
        roles=["admin"],
        profile_settings={},
        is_active=True,
    )
    inactive_user = User(
        email="inactivo@ucenfotec.ac.cr",
        display_name="Inactivo",
        password_hash=hash_password("1234ABC"),
        roles=["user"],
        profile_settings={},
        is_active=False,
    )
    indexed_manual = Manual(
        title="Manual Indexado",
        original_filename="indexed.pdf",
        storage_key="manuals/indexed.pdf",
        content_type="application/pdf",
        size_bytes=10,
        status="indexed",
        robot_model=None,
        controller_version=None,
        document_language="es",
        notes=None,
        uploaded_by_user_id=1,
        uploaded_by_email="activo@ucenfotec.ac.cr",
    )
    pending_manual = Manual(
        title="Manual Pendiente",
        original_filename="pending.pdf",
        storage_key="manuals/pending.pdf",
        content_type="application/pdf",
        size_bytes=10,
        status="pending",
        robot_model=None,
        controller_version=None,
        document_language="es",
        notes=None,
        uploaded_by_user_id=1,
        uploaded_by_email="activo@ucenfotec.ac.cr",
    )
    processing_manual = Manual(
        title="Manual Procesando",
        original_filename="processing.pdf",
        storage_key="manuals/processing.pdf",
        content_type="application/pdf",
        size_bytes=10,
        status="processing",
        robot_model=None,
        controller_version=None,
        document_language="es",
        notes=None,
        uploaded_by_user_id=1,
        uploaded_by_email="activo@ucenfotec.ac.cr",
    )

    db_session.add_all([active_user, inactive_user, indexed_manual, pending_manual, processing_manual])
    db_session.commit()

    response = client.get("/api/v1/admin/status")

    assert response.status_code == 200
    assert response.json() == {
        "manuals_indexed": 1,
        "active_users": 1,
        "pending_jobs": 2,
    }


def test_chat_generate_route_returns_placeholder_pac(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/generate",
        json={
            "prompt": "Genera una rutina de pick and place",
            "robot_type": "VP-6242",
            "controller": "RC7",
            "io_profile": "cell-a",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Respuesta de ejemplo para robot VP-6242 con controlador RC7."
    assert "PROGRAM SAMPLE_RC7" in payload["pac_code"]
    assert payload["references"] == [{"title": "Programmer's Manual I", "page": "3-24"}]
