from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import User
from src.db.models.settings import SystemSetting
from src.services.auth.passwords import hash_password


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


def _seed_settings(db_session: Session) -> None:
    """Insert a minimal set of settings rows for tests."""
    defaults = [
        ("gemini_temperature", "0.7", "Temperatura del modelo"),
        ("gemini_max_tokens", "2048", "Tokens máximos por respuesta"),
        ("history_max_entries", "50", "Entradas de historial máximas"),
    ]
    for key, value, description in defaults:
        row = SystemSetting(key=key, value=value, description=description)
        db_session.add(row)
    db_session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_list_settings_returns_all_rows(
    client: TestClient, db_session: Session
) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")
    _seed_settings(db_session)

    response = client.get("/api/v1/admin/settings")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    keys = {item["key"] for item in data["items"]}
    assert "gemini_temperature" in keys
    assert "gemini_max_tokens" in keys


def test_get_single_setting(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")
    _seed_settings(db_session)

    response = client.get("/api/v1/admin/settings/gemini_temperature")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "gemini_temperature"
    assert data["value"] == "0.7"


def test_get_setting_not_found(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")

    response = client.get("/api/v1/admin/settings/nonexistent_key")
    assert response.status_code == 404


def test_update_setting(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")
    _seed_settings(db_session)

    response = client.put(
        "/api/v1/admin/settings/gemini_temperature",
        json={"value": "0.9"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "gemini_temperature"
    assert data["value"] == "0.9"


def test_update_setting_not_found(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")

    response = client.put(
        "/api/v1/admin/settings/unknown_key",
        json={"value": "1.0"},
    )
    assert response.status_code == 404


def test_reset_settings(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session, email="admin@test.com", password="secret", roles=["admin", "user"]
    )
    login(client, "admin@test.com", "secret")
    _seed_settings(db_session)

    # Mutate a value first
    client.put("/api/v1/admin/settings/gemini_temperature", json={"value": "0.1"})

    response = client.post("/api/v1/admin/settings/reset")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    # After reset, gemini_temperature must be back to default
    temp_item = next(
        (i for i in data["items"] if i["key"] == "gemini_temperature"), None
    )
    assert temp_item is not None
    assert temp_item["value"] == "0.7"


def test_settings_require_admin_role(client: TestClient, db_session: Session) -> None:
    create_user(db_session, email="user@test.com", password="secret", roles=["user"])
    login(client, "user@test.com", "secret")

    response = client.get("/api/v1/admin/settings")
    assert response.status_code == 403
