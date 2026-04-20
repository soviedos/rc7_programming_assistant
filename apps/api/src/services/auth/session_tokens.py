from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from src.core.config import settings


def create_session_token(payload: dict[str, Any]) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.session_ttl_minutes)
    token_payload = {
        **payload,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(
        token_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_session_token(token: str) -> dict[str, Any]:
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise ValueError("Invalid session token") from exc

    return decoded
