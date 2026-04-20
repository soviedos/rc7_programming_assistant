from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import User
from src.services.auth.passwords import hash_password, verify_password


def create_user(
    db_session: Session,
    *,
    email: str,
    password: str,
    roles: list[str],
) -> User:
    user = User(
        email=email.strip().lower(),
        display_name="Sergio Oviedo",
        password_hash=hash_password(password),
        roles=roles,
        profile_settings={},
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "soviedo@ucenfotec.ac.cr",
            "password": "1234ABC",
        },
    )
    assert response.status_code == 200


def test_profile_returns_defaults_for_authorized_user(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client)

    response = client.get("/api/v1/profile")

    assert response.status_code == 200
    assert response.json() == {
        "email": "soviedo@ucenfotec.ac.cr",
        "display_name": "Sergio Oviedo",
        "settings": {
            "preferred_language": "es",
        },
    }


def test_profile_can_be_updated_and_persisted(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client)

    response = client.put(
        "/api/v1/profile",
        json={
            "display_name": "Ing. Sergio Oviedo",
            "settings": {
                "preferred_language": "en",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Ing. Sergio Oviedo"
    assert response.json()["settings"]["preferred_language"] == "en"

    refreshed_user = db_session.query(User).filter(User.email == "soviedo@ucenfotec.ac.cr").one()
    assert refreshed_user.display_name == "Ing. Sergio Oviedo"
    assert refreshed_user.profile_settings == {
        "preferred_language": "en",
    }


def test_password_change_requires_current_password(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client)

    response = client.post(
        "/api/v1/profile/password",
        json={
            "current_password": "incorrecta",
            "new_password": "ZXCV1234!",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "La contraseña actual no es correcta."


def test_password_change_updates_credentials(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client)

    response = client.post(
        "/api/v1/profile/password",
        json={
            "current_password": "1234ABC",
            "new_password": "Abcd1234!",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "La contraseña se actualizó correctamente.",
    }

    refreshed_user = db_session.query(User).filter(User.email == "soviedo@ucenfotec.ac.cr").one()
    assert verify_password("Abcd1234!", refreshed_user.password_hash) is True
    assert verify_password("1234ABC", refreshed_user.password_hash) is False


def test_password_change_enforces_rules(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client)

    response = client.post(
        "/api/v1/profile/password",
        json={
            "current_password": "1234ABC",
            "new_password": "abcdefghi",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "La nueva contraseña debe incluir al menos una letra mayúscula."


def test_password_change_rejects_passwords_longer_than_16_characters(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        email="soviedo@ucenfotec.ac.cr",
        password="1234ABC",
        roles=["admin", "user"],
    )
    login(client)

    response = client.post(
        "/api/v1/profile/password",
        json={
            "current_password": "1234ABC",
            "new_password": "Abcd1234!Efgh5678",
        },
    )

    assert response.status_code == 422
