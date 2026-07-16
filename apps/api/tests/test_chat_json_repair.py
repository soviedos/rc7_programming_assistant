"""Tests del parseo/reparación del JSON que devuelve Gemini.

Gemini a veces corta el stream a mitad del JSON sin agotar max_tokens. El payload
queda sin sus llaves de cierre, ``json.loads`` lo rechaza entero y la respuesta —
ya generada, con su summary y su pac_code completos — se perdía: el usuario recibía
el JSON crudo como resumen y CERO código. Medido: 2 de 5 ejecuciones del chat real.
"""

from __future__ import annotations

from src.services.chat.service import _parse_gemini_json, _repair_truncated_json


# ── _repair_truncated_json ─────────────────────────────────────────


def test_repair_closes_object_cut_after_a_complete_value() -> None:
    """El caso real: JSON completo al que solo le falta la llave de cierre."""
    truncado = '{"summary": "ok", "pac_code": "END", "references": ["S3"]'
    assert _repair_truncated_json(truncado) == (
        '{"summary": "ok", "pac_code": "END", "references": ["S3"]}'
    )


def test_repair_closes_nested_structures_in_order() -> None:
    truncado = '{"a": {"b": ["c"'
    assert _repair_truncated_json(truncado) == '{"a": {"b": ["c"]}}'


def test_repair_drops_a_value_cut_mid_string() -> None:
    """Cortado dentro de un string: se retrocede al último campo completo.

    Cerrar la comilla entregaría un valor a medias como si estuviera entero —
    peor que perderlo, porque nadie se enteraría.
    """
    truncado = '{"summary": "listo", "pac_code": "MOVE P, J1 y aqui se cor'
    reparado = _repair_truncated_json(truncado)
    assert reparado == '{"summary": "listo"}'


def test_repair_returns_none_for_complete_json() -> None:
    """Nada abierto = no es un truncamiento: no hay que tocar nada."""
    assert _repair_truncated_json('{"summary": "ok"}') is None


def test_repair_returns_none_when_nothing_is_recoverable() -> None:
    """Cortado en el primer valor, sin ningún campo completo detrás."""
    assert _repair_truncated_json('{"summary": "se corto aqui mism') is None


def test_repair_ignores_braces_inside_strings() -> None:
    """Una llave dentro de un string no abre estructura."""
    truncado = '{"summary": "usa { y } en el texto", "pac_code": "x"'
    assert _repair_truncated_json(truncado) == (
        '{"summary": "usa { y } en el texto", "pac_code": "x"}'
    )


def test_repair_handles_escaped_quotes() -> None:
    truncado = '{"summary": "dice \\"hola\\"", "pac_code": "x"'
    reparado = _repair_truncated_json(truncado)
    assert reparado is not None and reparado.endswith("}")


# ── _parse_gemini_json ─────────────────────────────────────────────


def test_parse_recovers_pac_code_from_truncated_payload() -> None:
    """Antes: summary = JSON crudo, pac_code = "". Ahora: ambos en su campo."""
    truncado = (
        '{\n  "summary": "Mueve los ejes",\n'
        '  "pac_code": "PROGRAM p\\n    TAKEARM\\n    DRIVEA (1, 45)\\nEND",\n'
        '  "references": ["S3"]'
    )
    data = _parse_gemini_json(truncado)

    assert data["summary"] == "Mueve los ejes"
    assert "DRIVEA (1, 45)" in data["pac_code"]
    assert "TAKEARM" in data["pac_code"]
    assert data["references"] == ["S3"]


def test_parse_still_handles_valid_json() -> None:
    data = _parse_gemini_json('{"summary": "s", "pac_code": "c", "references": []}')
    assert data == {"summary": "s", "pac_code": "c", "references": []}


def test_parse_still_handles_markdown_fences() -> None:
    data = _parse_gemini_json('```json\n{"summary": "s", "pac_code": "c"}\n```')
    assert data["summary"] == "s"
    assert data["pac_code"] == "c"


def test_parse_falls_back_to_summary_when_unrecoverable() -> None:
    """Sin JSON aprovechable, el texto entero sigue llegando como summary."""
    data = _parse_gemini_json("esto no es JSON en absoluto")
    assert data["summary"] == "esto no es JSON en absoluto"
    assert data["pac_code"] == ""
