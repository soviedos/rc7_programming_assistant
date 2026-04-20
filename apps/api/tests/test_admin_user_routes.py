from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import RolePermission, User
from src.services.auth.passwords import hash_password, verify_password


def create_user(
    db_session: Session,
    *,
    email: str,
    password: str,
    roles: list[str],
    display_name: str = "Usuario de prueba",
    is_active: bool = True,
) -> User:
    user = User(
        email=email.strip().lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        roles=roles,
        profile_settings={},
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client: TestClient, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def create_role_permission(
    db_session: Session,
    *,
    key: str,
    name: str,
    description: str,
    admin: bool,
    user: bool,
) -> RolePermission:
    permission = RolePermission(
        key=key,
        name=name,
        description=description,
        admin=admin,
        user=user,
    )
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


def test_admin_user_crud_flow(client: TestClient, db_session: Session) -> None:
    admin = create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="Abcd1234!",
        roles=["admin", "user"],
        display_name="Admin",
    )
    login(client, "admin@ucenfotec.ac.cr", "Abcd1234!")

    create_response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "operador@ucenfotec.ac.cr",
            "display_name": "Operador RC7",
            "password": "Secure123!",
            "role": "user",
            "is_active": True,
        },
    )

    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["email"] == "operador@ucenfotec.ac.cr"
    assert created_user["role"] == "user"

    list_response = client.get("/api/v1/admin/users")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2

    get_response = client.get(f"/api/v1/admin/users/{created_user['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["display_name"] == "Operador RC7"

    update_response = client.put(
        f"/api/v1/admin/users/{created_user['id']}",
        json={
            "display_name": "Operador Senior",
            "role": "admin",
            "is_active": True,
            "password": "Better123!",
        },
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["role"] == "admin"
    assert updated_payload["display_name"] == "Operador Senior"

    updated_user = db_session.get(User, created_user["id"])
    assert updated_user is not None
    assert verify_password("Better123!", updated_user.password_hash)

    delete_response = client.delete(f"/api/v1/admin/users/{created_user['id']}")
    assert delete_response.status_code == 204
    db_session.expire_all()
    assert db_session.get(User, created_user["id"]) is None

    self_delete_response = client.delete(f"/api/v1/admin/users/{admin.id}")
    assert self_delete_response.status_code == 400
    assert (
        self_delete_response.json()["detail"] == "No puedes eliminar tu propio usuario."
    )


def test_user_management_requires_admin_role(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="user@ucenfotec.ac.cr",
        password="User1234!",
        roles=["user"],
    )
    login(client, "user@ucenfotec.ac.cr", "User1234!")

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Se requiere una sesion activa con rol de administrador."
    )


def test_cannot_demote_or_deactivate_last_active_admin(
    client: TestClient, db_session: Session
) -> None:
    admin = create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="Admin1234!",
        roles=["admin", "user"],
    )
    login(client, "admin@ucenfotec.ac.cr", "Admin1234!")

    demote_response = client.put(
        f"/api/v1/admin/users/{admin.id}",
        json={
            "display_name": "Admin Principal",
            "role": "user",
            "is_active": True,
        },
    )

    assert demote_response.status_code == 400
    assert (
        demote_response.json()["detail"]
        == "No puedes quitarte el rol admin ni desactivar tu propio usuario."
    )

    deactivate_response = client.put(
        f"/api/v1/admin/users/{admin.id}",
        json={
            "display_name": "Admin Principal",
            "role": "admin",
            "is_active": False,
        },
    )

    assert deactivate_response.status_code == 400
    assert (
        deactivate_response.json()["detail"]
        == "No puedes quitarte el rol admin ni desactivar tu propio usuario."
    )


def test_create_user_rejects_duplicated_email(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="Admin1234!",
        roles=["admin", "user"],
    )
    create_user(
        db_session,
        email="existing@ucenfotec.ac.cr",
        password="User1234!",
        roles=["user"],
    )

    login(client, "admin@ucenfotec.ac.cr", "Admin1234!")

    response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "existing@ucenfotec.ac.cr",
            "display_name": "Duplicado",
            "password": "Secure123!",
            "role": "user",
            "is_active": True,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un usuario con ese correo."


def test_role_permissions_returns_matrix_for_admin(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="Admin1234!",
        roles=["admin", "user"],
    )
    create_role_permission(
        db_session,
        key="manuals",
        name="Manuales",
        description="Ver, subir y gestionar la base documental.",
        admin=True,
        user=False,
    )
    create_role_permission(
        db_session,
        key="chat",
        name="Chat",
        description="Usar el asistente para consultas tecnicas.",
        admin=True,
        user=True,
    )
    login(client, "admin@ucenfotec.ac.cr", "Admin1234!")

    response = client.get("/api/v1/admin/roles/permissions")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) == 2
    assert [item["key"] for item in payload["items"]] == ["chat", "manuals"]


def test_role_permissions_requires_admin_role(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="user@ucenfotec.ac.cr",
        password="User1234!",
        roles=["user"],
    )
    login(client, "user@ucenfotec.ac.cr", "User1234!")

    response = client.get("/api/v1/admin/roles/permissions")

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Se requiere una sesion activa con rol de administrador."
    )


def test_role_permissions_crud_for_admin(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="Admin1234!",
        roles=["admin", "user"],
    )
    login(client, "admin@ucenfotec.ac.cr", "Admin1234!")

    create_response = client.post(
        "/api/v1/admin/roles/permissions",
        json={
            "key": "reports",
            "name": "Reportes",
            "description": "Permite visualizar reportes de uso.",
            "admin": True,
            "user": False,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["key"] == "reports"

    update_response = client.put(
        f"/api/v1/admin/roles/permissions/{created['id']}",
        json={
            "name": "Reportes y metricas",
            "description": "Permite visualizar reportes y metricas del sistema.",
            "admin": True,
            "user": True,
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Reportes y metricas"
    assert updated["user"] is True

    delete_response = client.delete(f"/api/v1/admin/roles/permissions/{created['id']}")
    assert delete_response.status_code == 204

    list_response = client.get("/api/v1/admin/roles/permissions")
    assert list_response.status_code == 200
    assert all(item["key"] != "reports" for item in list_response.json()["items"])


def test_role_permissions_create_rejects_duplicated_key(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session,
        email="admin@ucenfotec.ac.cr",
        password="Admin1234!",
        roles=["admin", "user"],
    )
    create_role_permission(
        db_session,
        key="reports",
        name="Reportes",
        description="Permite visualizar reportes de uso.",
        admin=True,
        user=False,
    )
    login(client, "admin@ucenfotec.ac.cr", "Admin1234!")

    response = client.post(
        "/api/v1/admin/roles/permissions",
        json={
            "key": "reports",
            "name": "Duplicado",
            "description": "Intento duplicado.",
            "admin": True,
            "user": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un permiso con esa clave."
