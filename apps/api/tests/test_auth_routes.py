from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import User
from src.services.auth.passwords import hash_password


def create_user(
    db_session: Session,
    *,
    email: str,
    password: str,
    roles: list[str],
    is_active: bool = True,
) -> User:
    user = User(
        email=email.strip().lower(),
        display_name="Usuario de prueba",
        password_hash=hash_password(password),
        roles=roles,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_me_switch_role_and_logout(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "soviedo@ucenfotec.ac.cr",
            "password": "1234ABC",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["role"] == "admin"
    assert login_response.json()["redirect_path"] == "/admin"
    assert "set-cookie" in login_response.headers

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "soviedo@ucenfotec.ac.cr"
    assert me_response.json()["available_roles"] == ["admin", "user"]

    switch_response = client.post(
        "/api/v1/auth/switch-role",
        json={"role": "user"},
    )
    assert switch_response.status_code == 200
    assert switch_response.json()["role"] == "user"
    assert switch_response.json()["redirect_path"] == "/app"

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"success": True}

    me_after_logout_response = client.get("/api/v1/auth/me")
    assert me_after_logout_response.status_code == 401
    assert me_after_logout_response.json()["detail"] == "No hay una sesión activa."


def test_login_rejects_invalid_credentials(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "soviedo@ucenfotec.ac.cr",
            "password": "incorrecta",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales invalidas."


def test_login_rejects_inactive_users(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="inactivo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["user"],
        is_active=False,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactivo@ucenfotec.ac.cr",
            "password": "1234ABC",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales invalidas."


def test_switch_role_rejects_roles_not_assigned(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="usuario@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["user"],
    )

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "usuario@ucenfotec.ac.cr",
            "password": "1234ABC",
        },
    )

    response = client.post(
        "/api/v1/auth/switch-role",
        json={"role": "admin"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Ese usuario no tiene permiso para usar ese rol."


def test_login_validates_required_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert len(detail) == 2
