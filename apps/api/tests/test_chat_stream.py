"""Tests for the SSE streaming chat endpoint (/api/v1/chat/generate)."""
from __future__ import annotations

import json
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import User
from src.services.auth.passwords import hash_password

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHAT_PAYLOAD = {
    "prompt": "¿Cómo programo un pick and place?",
    "robot_type": "VS060",
    "controller": "RC7",
    "io_profile": "16I/16O",
    "payload_kg": 3,
    "tool_number": 1,
    "max_speed_pct": 80,
    "hand_type": "pneumatic_single",
    "install_type": "floor",
    "has_io_expansion": False,
    "expansion_io_inputs": 0,
    "expansion_io_outputs": 0,
    "current_code": "",
}


def _make_user(db: Session, email: str, password: str, role: str = "user") -> User:
    user = User(
        email=email,
        display_name="Test User",
        password_hash=hash_password(password),
        roles=[role],
        profile_settings={},
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _login(client: TestClient, email: str, password: str) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200


def _parse_sse_events(raw: str) -> list[dict]:
    """Parse SSE text body into a list of decoded event dicts."""
    events = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_chat_stream_yields_chunks_and_done_event(
    client: TestClient,
    db_session: Session,
) -> None:
    """Authenticated POST to /generate returns SSE with chunk + done events."""
    _make_user(db_session, "stream@test.com", "Stream1234")
    _login(client, "stream@test.com", "Stream1234")

    fake_sse: list[str] = [
        'data: {"type": "chunk", "content": "Primero"}\n\n',
        'data: {"type": "chunk", "content": " segundo"}\n\n',
        'data: {"type": "done", "summary": "Primero segundo", "pac_code": "", "references": []}\n\n',
    ]

    def _fake_stream(*_args, **_kwargs) -> Iterator[str]:
        yield from fake_sse

    with patch("src.api.v1.routes.chat.stream_rag_response", side_effect=_fake_stream):
        resp = client.post("/api/v1/chat/generate", json=_CHAT_PAYLOAD)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse_events(resp.text)
    types = [e["type"] for e in events]
    assert "chunk" in types
    assert "done" in types

    done_event = next(e for e in events if e["type"] == "done")
    assert done_event["summary"] == "Primero segundo"
    assert done_event["pac_code"] == ""


def test_chat_stream_unauthenticated_returns_401(client: TestClient) -> None:
    """Unauthenticated request is rejected before the stream begins."""
    resp = client.post("/api/v1/chat/generate", json=_CHAT_PAYLOAD)
    assert resp.status_code == 401


def test_chat_stream_pipeline_error_yields_error_event(
    client: TestClient,
    db_session: Session,
) -> None:
    """If stream_rag_response raises, the endpoint yields an SSE error event."""
    _make_user(db_session, "errstream@test.com", "Stream1234")
    _login(client, "errstream@test.com", "Stream1234")

    def _boom(*_args, **_kwargs) -> Iterator[str]:
        raise RuntimeError("Pipeline exploded")
        yield  # make it a generator

    with patch("src.api.v1.routes.chat.stream_rag_response", side_effect=_boom):
        resp = client.post("/api/v1/chat/generate", json=_CHAT_PAYLOAD)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse_events(resp.text)
    assert any(e.get("type") == "error" for e in events)
