"""Tests del parseo/reparación del JSON que devuelve Gemini.

Gemini estropea el JSON de dos maneras opuestas, y ambas se veían igual desde la
UI: el historial mostraba el JSON crudo como resumen y el canvas se quedaba vacío,
porque _parse_gemini_json cae a {"summary": texto_entero, "pac_code": ""}.

1. TRUNCADO — corta el stream a mitad del JSON, sin agotar max_tokens, y el
   payload queda sin cerrar. Medido: 2 de 5 ejecuciones del chat real.
2. BASURA DETRÁS — cierra bien el objeto y escribe un "}" de más al final.
   json.loads rechaza el texto ENTERO ("Extra data") aunque la respuesta esté
   completa. Medido: 6 de 48 respuestas guardadas en el historial real.

Los dos se recuperan: el primero cerrando lo que quedó abierto, el segundo con
raw_decode, que parsea el primer valor completo e ignora lo que sobre.
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


# ── Basura después del JSON ("Extra data") ─────────────────────────


def test_parse_ignores_the_extra_closing_brace_gemini_appends() -> None:
    """El caso real medido: objeto completo + "}" de sobra.

    Reproduce lo guardado en el historial (id=49): json.loads muere con "Extra
    data" y, sin esto, la respuesta entera se tiraba por una llave sobrante.
    """
    con_sobra = (
        '{\n  "summary": "Mueve los ejes",\n'
        '  "pac_code": "PROGRAM p\\n    DRIVEA (1, 45)\\nEND",\n'
        '  "references": ["S5", "S18"]\n}\n}'
    )
    data = _parse_gemini_json(con_sobra)

    assert data["summary"] == "Mueve los ejes"
    assert "DRIVEA (1, 45)" in data["pac_code"]
    assert data["references"] == ["S5", "S18"]


def test_parse_ignores_trailing_prose_after_the_json() -> None:
    """Cualquier cola sobra, no solo una llave: raw_decode corta en el objeto."""
    data = _parse_gemini_json(
        '{"summary": "s", "pac_code": "END", "references": []}\n'
        "Espero que te sirva."
    )
    assert data["summary"] == "s"
    assert data["pac_code"] == "END"


def test_parse_ignores_prose_before_the_json() -> None:
    data = _parse_gemini_json(
        'Aquí tienes:\n{"summary": "s", "pac_code": "END", "references": []}'
    )
    assert data["pac_code"] == "END"


def test_parse_keeps_braces_that_live_inside_the_code() -> None:
    """La llave de cierre buena no es la última del texto: no vale ir al final.

    El regex greedy que había antes (r"\{.*\}") se llevaba hasta el último "}"
    del texto, que es justo la basura que había que descartar.
    """
    data = _parse_gemini_json(
        '{"summary": "s", "pac_code": "IF x THEN {y}", "references": []}\n}'
    )
    assert data["pac_code"] == "IF x THEN {y}"


def test_parse_falls_back_to_summary_when_unrecoverable() -> None:
    """Sin JSON aprovechable, el texto entero sigue llegando como summary."""
    data = _parse_gemini_json("esto no es JSON en absoluto")
    assert data["summary"] == "esto no es JSON en absoluto"
    assert data["pac_code"] == ""
