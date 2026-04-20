from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.v1.routes.manuals import get_manual_storage_service
from src.db.models import Manual, User
from src.services.auth.passwords import hash_password


class FakeManualStorageService:
    def __init__(self) -> None:
        self.uploads: list[dict[str, object]] = []
        self.objects: dict[str, bytes] = {}
        self.removed_keys: list[str] = []

    def upload_manual(
        self, content: bytes, storage_key: str, content_type: str
    ) -> None:
        self.uploads.append(
            {
                "content": content,
                "storage_key": storage_key,
                "content_type": content_type,
            }
        )
        self.objects[storage_key] = content

    def download_manual(self, storage_key: str) -> bytes:
        return self.objects[storage_key]

    def delete_manual(self, storage_key: str) -> None:
        self.removed_keys.append(storage_key)
        self.objects.pop(storage_key, None)


def create_user(
    db_session: Session,
    *,
    email: str,
    password: str,
    roles: list[str],
) -> User:
    user = User(
        email=email.strip().lower(),
        display_name="Usuario Manuales",
        password_hash=hash_password(password),
        roles=roles,
        profile_settings={},
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client: TestClient, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 200


def test_manual_upload_requires_admin_role(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="operador@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["user"],
    )
    login(client, "operador@ucenfotec.ac.cr", "1234ABC")

    response = client.post(
        "/api/v1/manuals",
        data={"title": "RC7 Programmer Manual"},
        files={"file": ("manual.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Se requiere una sesion activa con rol de administrador."
    )


def test_manual_upload_persists_metadata_and_stores_pdf(
    client: TestClient,
    db_session: Session,
) -> None:
    fake_storage = FakeManualStorageService()
    client.app.dependency_overrides[get_manual_storage_service] = lambda: fake_storage

    try:
        admin = create_user(
            db_session,
            email="admin@ucenfotec.ac.cr",
            password="1234ABC",
            roles=["admin", "user"],
        )
        login(client, "admin@ucenfotec.ac.cr", "1234ABC")

        response = client.post(
            "/api/v1/manuals",
            data={
                "title": "RC7 Programmer Manual I",
                "robot_model": "VP-6242",
                "controller_version": "RC7.2",
                "document_language": "en",
                "notes": "Manual base para programacion PAC.",
            },
            files={
                "file": (
                    "rc7-programmer-manual.pdf",
                    b"%PDF-1.4 manual content",
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["title"] == "RC7 Programmer Manual I"
        assert payload["status"] == "pending"
        assert payload["robot_model"] == "VP-6242"
        assert payload["controller_version"] == "RC7.2"
        assert payload["document_language"] == "en"
        assert payload["uploaded_by_user_id"] == admin.id
        assert payload["uploaded_by_email"] == "admin@ucenfotec.ac.cr"
        assert payload["original_filename"] == "rc7-programmer-manual.pdf"
        assert payload["storage_key"].startswith("manuals/")
        assert payload["storage_key"].endswith(".pdf")
        assert payload["size_bytes"] == len(b"%PDF-1.4 manual content")

        assert len(fake_storage.uploads) == 1
        assert fake_storage.uploads[0]["content"] == b"%PDF-1.4 manual content"
        assert fake_storage.uploads[0]["content_type"] == "application/pdf"
        assert fake_storage.uploads[0]["storage_key"] == payload["storage_key"]

        manual = db_session.get(Manual, payload["id"])
        assert manual is not None
        assert manual.title == "RC7 Programmer Manual I"
        assert manual.status == "pending"
        assert manual.uploaded_by_email == "admin@ucenfotec.ac.cr"
    finally:
        client.app.dependency_overrides.pop(get_manual_storage_service, None)


def test_manual_list_and_detail_return_registered_manuals(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client, "admin@ucenfotec.ac.cr", "1234ABC")

    older_manual = Manual(
        title="Manual Antiguo",
        original_filename="old.pdf",
        storage_key="manuals/2026/04/20/old.pdf",
        content_type="application/pdf",
        size_bytes=10,
        status="indexed",
        robot_model="VS-6556",
        controller_version="RC7.1",
        document_language="es",
        notes=None,
        uploaded_by_user_id=admin.id,
        uploaded_by_email=admin.email,
    )
    newer_manual = Manual(
        title="Manual Nuevo",
        original_filename="new.pdf",
        storage_key="manuals/2026/04/20/new.pdf",
        content_type="application/pdf",
        size_bytes=20,
        status="pending",
        robot_model="VP-6242",
        controller_version="RC7.2",
        document_language="en",
        notes="Pendiente de indexacion.",
        uploaded_by_user_id=admin.id,
        uploaded_by_email=admin.email,
    )
    db_session.add(older_manual)
    db_session.add(newer_manual)
    db_session.commit()
    db_session.refresh(older_manual)
    db_session.refresh(newer_manual)

    list_response = client.get("/api/v1/manuals")

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 2
    assert [item["title"] for item in payload["items"]] == [
        "Manual Nuevo",
        "Manual Antiguo",
    ]

    detail_response = client.get(f"/api/v1/manuals/{older_manual.id}")

    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Manual Antiguo"
    assert detail_response.json()["status"] == "indexed"


def test_manual_upload_rejects_non_pdf_files(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client, "admin@ucenfotec.ac.cr", "1234ABC")

    response = client.post(
        "/api/v1/manuals",
        data={"title": "Archivo invalido"},
        files={"file": ("manual.txt", b"texto plano", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Solo se permiten archivos PDF."


def test_manual_update_open_and_delete_flow(
    client: TestClient, db_session: Session
) -> None:
    fake_storage = FakeManualStorageService()
    client.app.dependency_overrides[get_manual_storage_service] = lambda: fake_storage

    try:
        admin = create_user(
            db_session,
            email="admin@ucenfotec.ac.cr",
            password="1234ABC",
            roles=["admin", "user"],
        )
        login(client, "admin@ucenfotec.ac.cr", "1234ABC")

        manual = Manual(
            title="Manual Inicial",
            original_filename="initial.pdf",
            storage_key="manuals/2026/04/20/initial.pdf",
            content_type="application/pdf",
            size_bytes=25,
            status="indexed",
            chunk_count=4,
            robot_model="VP-6242",
            controller_version="RC7",
            document_language="es",
            notes=None,
            uploaded_by_user_id=admin.id,
            uploaded_by_email=admin.email,
        )
        db_session.add(manual)
        db_session.commit()
        db_session.refresh(manual)
        manual_id = manual.id
        fake_storage.objects[manual.storage_key] = b"%PDF-1.4 test content"

        update_response = client.put(
            f"/api/v1/manuals/{manual_id}",
            json={
                "title": "Manual Actualizado",
                "notes": "Nota importante",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Manual Actualizado"
        assert update_response.json()["notes"] == "Nota importante"

        open_response = client.get(f"/api/v1/manuals/{manual_id}/file")
        assert open_response.status_code == 200
        assert open_response.content == b"%PDF-1.4 test content"
        assert open_response.headers["content-type"].startswith("application/pdf")

        delete_response = client.delete(f"/api/v1/manuals/{manual_id}")
        assert delete_response.status_code == 204
        assert manual.storage_key in fake_storage.removed_keys

        db_session.expire_all()
        assert db_session.get(Manual, manual_id) is None
    finally:
        client.app.dependency_overrides.pop(get_manual_storage_service, None)
