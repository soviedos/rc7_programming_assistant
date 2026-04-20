from sqlalchemy.orm import Session

from src.db.models import User
from src.services.auth.passwords import hash_password, verify_password
from src.services.auth.session_tokens import create_session_token, decode_session_token
from src.services.auth.users import build_session_response, normalize_roles


def test_hash_password_and_verify_roundtrip() -> None:
    password_hash = hash_password("1234ABC")

    assert password_hash != "1234ABC"
    assert verify_password("1234ABC", password_hash) is True
    assert verify_password("bad-password", password_hash) is False


def test_normalize_roles_filters_unknown_roles() -> None:
    assert normalize_roles(["operator", "user", "guest", "admin"]) == ["user", "admin"]
    assert normalize_roles(["operator", "guest"]) == ["user"]


def test_build_session_response_uses_first_available_role_when_needed() -> None:
    user = User(
        email="soviedo@ucenfotec.ac.cr",
        display_name="Sergio Oviedo",
        password_hash="hash",
        roles=["admin", "user"],
        is_active=True,
    )

    session_response = build_session_response(user, "user")

    assert session_response.email == "soviedo@ucenfotec.ac.cr"
    assert session_response.role == "user"
    assert session_response.available_roles == ["admin", "user"]
    assert session_response.redirect_path == "/app"


def test_session_token_roundtrip() -> None:
    token = create_session_token(
        {
            "sub": "1",
            "email": "soviedo@ucenfotec.ac.cr",
            "display_name": "Sergio Oviedo",
            "role": "admin",
            "available_roles": ["admin", "user"],
        }
    )

    payload = decode_session_token(token)

    assert payload["email"] == "soviedo@ucenfotec.ac.cr"
    assert payload["role"] == "admin"
    assert payload["available_roles"] == ["admin", "user"]
