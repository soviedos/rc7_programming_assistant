"""Tests for RAG source-traceability in the chat service.

Covers the source-ID (`S1`, `S2`, …) reference resolution and the system-prompt
instructions that bind each generated PAC instruction to its retrieved source.
"""

from __future__ import annotations

from src.api.v1.schemas.chat import ChatRequest
from src.services.chat import service as chat_service
from src.services.chat.service import _build_system_prompt, _resolve_references


class _ManualStub:
    def __init__(self, title: str) -> None:
        self.title = title


def _make_source_map() -> dict[str, tuple[_ManualStub, int]]:
    return {
        "S1": (_ManualStub("Programmer Manual"), 12),
        "S2": (_ManualStub("Startup Guide"), 45),
        "S3": (_ManualStub("Programmer Manual"), 12),  # dup title:page of S1
    }


# ---------------------------------------------------------------------------
# _resolve_references
# ---------------------------------------------------------------------------


def test_resolve_references_keeps_only_cited_valid_ids() -> None:
    source_map = _make_source_map()
    refs = _resolve_references(["S1", "S2"], source_map)
    assert refs == [("Programmer Manual", "12"), ("Startup Guide", "45")]


def test_resolve_references_discards_hallucinated_ids() -> None:
    source_map = _make_source_map()
    # S9 is not in the context — must be dropped, leaving only S2.
    refs = _resolve_references(["S9", "S2"], source_map)
    assert refs == [("Startup Guide", "45")]


def test_resolve_references_falls_back_to_full_set_when_none_valid() -> None:
    source_map = _make_source_map()
    refs = _resolve_references(["S42", "nonsense"], source_map)
    # Fallback to every retrieved source, deduplicated by title:page.
    assert refs == [("Programmer Manual", "12"), ("Startup Guide", "45")]


def test_resolve_references_empty_falls_back_to_full_set() -> None:
    source_map = _make_source_map()
    assert _resolve_references([], source_map) == [
        ("Programmer Manual", "12"),
        ("Startup Guide", "45"),
    ]


def test_resolve_references_dedups_repeated_sources() -> None:
    source_map = _make_source_map()
    # S1 and S3 share the same title:page — only one entry survives.
    refs = _resolve_references(["S1", "S3"], source_map)
    assert refs == [("Programmer Manual", "12")]


def test_resolve_references_extracts_ids_from_strings() -> None:
    source_map = _make_source_map()
    # Model may echo IDs embedded in free text instead of a clean list.
    refs = _resolve_references("usé S2 y también S1", source_map)
    assert refs == [("Startup Guide", "45"), ("Programmer Manual", "12")]


def test_resolve_references_handles_none() -> None:
    source_map = _make_source_map()
    # None → no cited IDs → fallback to full set.
    assert _resolve_references(None, source_map) == [
        ("Programmer Manual", "12"),
        ("Startup Guide", "45"),
    ]


def test_resolve_references_empty_source_map_returns_empty() -> None:
    assert _resolve_references(["S1"], {}) == []


# ---------------------------------------------------------------------------
# _build_system_prompt — traceability instructions
# ---------------------------------------------------------------------------


def test_system_prompt_requires_inline_source_comments(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_service, "get_setting_value", lambda *_a, **_k: "REGLAS PAC"
    )
    payload = ChatRequest(prompt="¿Cómo muevo el robot?")

    prompt = _build_system_prompt(db=None, payload=payload)  # type: ignore[arg-type]

    # Inline traceability comment using the PAC apostrophe syntax.
    assert "' fuente: S2" in prompt
    # references must carry the used source IDs, not be a fixed empty array.
    assert '["S1","S3"]' in prompt
    # Example response shows a source comment and a populated references array.
    assert "' fuente: S1" in prompt
    assert '"references":["S1"]' in prompt
    # Hallucinated IDs are explicitly forbidden.
    assert "NUNCA inventes IDs" in prompt
