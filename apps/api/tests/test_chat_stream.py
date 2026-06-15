"""Tests for the SSE streaming chat endpoint (/api/v1/chat/generate)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import ChatHistory, User
from tests.helpers import create_user, login

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
    create_user(
        db_session, email="stream@test.com", password="Stream1234", roles=["user"]
    )
    login(client, "stream@test.com", "Stream1234")

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
    create_user(
        db_session, email="errstream@test.com", password="Stream1234", roles=["user"]
    )
    login(client, "errstream@test.com", "Stream1234")

    def _boom(*_args, **_kwargs) -> Iterator[str]:
        raise RuntimeError("Pipeline exploded")
        yield  # make it a generator

    with patch("src.api.v1.routes.chat.stream_rag_response", side_effect=_boom):
        resp = client.post("/api/v1/chat/generate", json=_CHAT_PAYLOAD)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse_events(resp.text)
    assert any(e.get("type") == "error" for e in events)


def test_chat_history_persists_and_returns_source_id(
    client: TestClient,
    db_session: Session,
) -> None:
    """References (with source_id) survive in chat_history and round-trip via GET."""
    user = create_user(
        db_session, email="hist@test.com", password="Hist1234", roles=["user"]
    )
    login(client, "hist@test.com", "Hist1234")

    db_session.add(
        ChatHistory(
            user_id=user.id,
            prompt="¿pick and place?",
            summary="Programa generado.",
            pac_code="PROGRAM p\n    MOVE P, P1    ' fuente: S1\nEND",
            references=[
                {"source_id": "S1", "title": "Programmer Manual", "page": "12"},
                {"source_id": "S2", "title": "Startup Guide", "page": "45"},
            ],
            robot_config={},
            entry_type="code",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/chat/history")
    assert resp.status_code == 200
    refs = resp.json()["items"][0]["references"]
    assert refs == [
        {"source_id": "S1", "title": "Programmer Manual", "page": "12"},
        {"source_id": "S2", "title": "Startup Guide", "page": "45"},
    ]


def test_chat_history_recomputes_advisories_from_pac_code(
    client: TestClient,
    db_session: Session,
) -> None:
    """History derives level-2 advisories deterministically from stored pac_code."""
    user = create_user(
        db_session, email="adv@test.com", password="Advis1234", roles=["user"]
    )
    login(client, "adv@test.com", "Advis1234")

    # Step motion (@P) immediately before actuating an output → 1 advisory.
    db_session.add(
        ChatHistory(
            user_id=user.id,
            prompt="recoge la pieza",
            summary="Programa generado.",
            pac_code="PROGRAM p\n    MOVE P, @P P[pPick]\n    SET IO[ioGrip]\nEND",
            references=[],
            robot_config={},
            entry_type="code",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/chat/history")
    assert resp.status_code == 200
    advisories = resp.json()["items"][0]["advisories"]
    assert len(advisories) == 1
    assert advisories[0].startswith("Línea 2:")  # the MOVE @P line in stored code
    assert "movimiento de paso" in advisories[0]
