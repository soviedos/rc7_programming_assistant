"""Shared test helper functions for API tests.

These are plain functions (not fixtures) used across multiple test modules
to avoid duplicating user-creation and login boilerplate.
"""

from __future__ import annotations

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
