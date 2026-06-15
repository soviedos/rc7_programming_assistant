"""Tests for RAG source-traceability in the chat service.

The source legend (`S1`, `S2`, …) is built solely from the saved ``source_map``
so every inline ``' fuente: SX`` comment in the generated PAC code resolves to a
``(source_id, title, page)`` entry — the model never decodes a SID itself.
"""

from __future__ import annotations

import re

from src.api.v1.schemas.chat import ChatRequest, ReferenceItem
from src.services.chat import service as chat_service
from src.services.chat.service import (
    _build_system_prompt,
    _prepend_source_legend,
    _resolve_references,
)
from src.services.settings.service import _DEFAULT_PAC_RULES


class _ManualStub:
    def __init__(self, title: str) -> None:
        self.title = title


def _make_source_map() -> dict[str, tuple[_ManualStub, int]]:
    return {
        "S1": (_ManualStub("Programmer Manual"), 12),
        "S2": (_ManualStub("Startup Guide"), 45),
        "S3": (_ManualStub("Programmer Manual"), 12),  # same title:page as S1
    }


# ---------------------------------------------------------------------------
# _resolve_references — the full legend, one entry per SID
# ---------------------------------------------------------------------------


def test_resolve_references_returns_every_sid_ordered() -> None:
    """One entry per SID in source_map, ordered S1…Sn, with (source_id,title,page)."""
    refs = _resolve_references(_make_source_map())
    assert refs == [
        ("S1", "Programmer Manual", "12"),
        ("S2", "Startup Guide", "45"),
        ("S3", "Programmer Manual", "12"),  # NOT deduped: distinct SID = distinct entry
    ]


def test_resolve_references_orders_numerically_not_lexically() -> None:
    """S2 must come before S10 (numeric order), regardless of insertion order."""
    source_map = {
        "S10": (_ManualStub("Tenth"), 100),
        "S2": (_ManualStub("Second"), 2),
        "S1": (_ManualStub("First"), 1),
    }
    assert [sid for sid, _t, _p in _resolve_references(source_map)] == ["S1", "S2", "S10"]


def test_resolve_references_empty_source_map_returns_empty() -> None:
    assert _resolve_references({}) == []


def test_every_cited_sid_in_pac_code_has_reference_with_source_id() -> None:
    """Each SID cited inline in pac_code resolves to a references entry w/ source_id."""
    source_map = _make_source_map()
    references = [
        ReferenceItem(source_id=sid, title=title, page=page)
        for sid, title, page in _resolve_references(source_map)
    ]
    legend_ids = {r.source_id for r in references}

    pac_code = (
        "PROGRAM pickPlace\n"
        "    TAKEARM\n"
        "    MOVE P, P1    ' fuente: S2\n"
        "    GOSUB *Place  ' fuente: S1\n"
        "    GIVEARM\n"
        "END\n"
    )
    cited = set(re.findall(r"S\d+", pac_code))

    # No inline ' fuente: SX is left unresolved, and every reference carries its ID.
    assert cited, "the sample code must cite at least one SID"
    assert cited <= legend_ids
    assert all(r.source_id for r in references)


# ---------------------------------------------------------------------------
# _prepend_source_legend — self-contained .pac legend
# ---------------------------------------------------------------------------


def test_prepend_source_legend_builds_deterministic_block() -> None:
    code = "PROGRAM p\n    MOVE P, P1    ' fuente: S2\nEND"
    out = _prepend_source_legend(code, _make_source_map())
    lines = out.split("\n")
    assert lines[0] == "' ─── Fuentes (trazabilidad) ───"
    assert lines[1] == "' S1 = Programmer Manual, pág. 12"
    assert lines[2] == "' S2 = Startup Guide, pág. 45"
    assert lines[3] == "' S3 = Programmer Manual, pág. 12"
    assert lines[4] == "' ──────────────────────────────"
    # Every legend line is a valid PAC comment (apostrophe) and the original
    # code is preserved verbatim after the block.
    assert all(line.startswith("'") for line in lines[:5])
    assert out.endswith(code)


def test_prepend_source_legend_noop_on_empty_code() -> None:
    assert _prepend_source_legend("", _make_source_map()) == ""


def test_prepend_source_legend_noop_when_no_sources() -> None:
    code = "PROGRAM p\nEND"
    assert _prepend_source_legend(code, {}) == code


# ---------------------------------------------------------------------------
# System prompt — traceability instructions + SID guardrail
# ---------------------------------------------------------------------------


def test_system_prompt_requires_inline_source_comments(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_service, "get_setting_value", lambda *_a, **_k: "REGLAS PAC"
    )
    payload = ChatRequest(prompt="¿Cómo muevo el robot?")

    prompt = _build_system_prompt(db=None, payload=payload)  # type: ignore[arg-type]

    assert "' fuente: S2" in prompt
    assert '["S1","S3"]' in prompt
    assert "' fuente: S1" in prompt
    assert '"references":["S1"]' in prompt
    assert "NUNCA inventes IDs" in prompt


def test_system_prompt_pac_default_has_sid_guardrail() -> None:
    """The PAC rules forbid the model from decoding/inventing a SID's source."""
    assert "etiquetas de trazabilidad asignadas por el sistema" in _DEFAULT_PAC_RULES
    assert "NUNCA inventes ni expliques a qué manual corresponde un SX" in _DEFAULT_PAC_RULES
    assert "consulte la leyenda de fuentes" in _DEFAULT_PAC_RULES
