"""Tests de la leyenda de fuentes: debe declarar en qué se BASA el código.

El recuperador trae top-k chunks y varios suelen ser ruido (prefacios, índices,
tutoriales del IDE). La leyenda los listaba todos, así que un programa sostenido
por UNA página anunciaba seis fuentes: quien fuera a comprobarlas encontraba
"Chapter 1 Overview" o "Creating a New Project". Caso real medido: 6 fuentes en la
leyenda, 1 citada en el código.
"""

from __future__ import annotations

from src.services.chat.service import (
    _cited_source_ids,
    _prepend_source_legend,
    _resolve_references,
)


class _FakeManual:
    def __init__(self, title: str) -> None:
        self.title = title


def _source_map() -> dict:
    """El source_map real de la respuesta que motivó este cambio."""
    return {
        "S1": (_FakeManual("program1 e"), 181),  # 7.1 New Robot Language PAC
        "S2": (_FakeManual("program1 e"), 312),  # 12.1 Motion Control  ← la buena
        "S3": (_FakeManual("program1 e"), 189),  # 7.5.4 Program
        "S4": (_FakeManual("startup e"), 115),  # 11.3.2 Creating a New Project
        "S5": (_FakeManual("wincaps3 e"), 9),  # 1.2 Robot Controller and WINCAPS
        "S6": (_FakeManual("program1 e"), 319),  # 12.1 Motion Control
    }


# ── _cited_source_ids ──────────────────────────────────────────────


def test_cited_ids_finds_inline_citations() -> None:
    code = "    DRIVEA (1, 45)    ' Mueve el eje 1 ' fuente: S2"
    assert _cited_source_ids(code) == {"S2"}


def test_cited_ids_accepts_the_parenthesised_form() -> None:
    """El modelo no siempre sigue el formato que pide el prompt.

    El prompt enseña `' fuente: S2`, pero en respuestas reales también escribe
    `' comentario (fuente: S2)`. Anclar el patrón al apóstrofo dejaba fuera esa
    variante: el filtro no veía citas y la leyenda caía al mapa completo — el
    bug que devolvió 6 fuentes para un código que citaba 2.
    """
    code = (
        "    TAKEARM                    ' Obtiene el control del brazo (fuente: S2)\n"
        "    DRIVEA (1, 45), (2, -30)   ' Mueve eje 1 a 45 grados (fuente: S3)"
    )
    assert _cited_source_ids(code) == {"S2", "S3"}


def test_cited_ids_accepts_both_forms_in_one_program() -> None:
    code = "A ' fuente: S1\nB ' texto (fuente: S2)\nC ' texto ' fuente: S3"
    assert _cited_source_ids(code) == {"S1", "S2", "S3"}


def test_cited_ids_does_not_match_the_legend_block_itself() -> None:
    """La leyenda ya anotada no debe contarse como cita."""
    legend = (
        "' ─── Fuentes (trazabilidad) ───\n"
        "' S1 = program1 e, pág. 181\n"
        "' S2 = program1 e, pág. 312\n"
        "' ──────────────────────────────"
    )
    assert _cited_source_ids(legend) == set()


def test_cited_ids_is_case_insensitive_and_deduplicates() -> None:
    code = "A ' fuente: S2\nB ' FUENTE: s2\nC ' fuente: S6"
    assert _cited_source_ids(code) == {"S2", "S6"}


def test_cited_ids_empty_for_code_without_citations() -> None:
    assert _cited_source_ids("PROGRAM p\nEND") == set()
    assert _cited_source_ids("") == set()


# ── _resolve_references ────────────────────────────────────────────


def test_legend_lists_only_what_the_code_cites() -> None:
    """El caso real: 6 recuperadas, 1 citada."""
    pac = "    DRIVEA (1, 45), (2, -30)    ' fuente: S2"
    refs = _resolve_references(_source_map(), pac)

    assert refs == [("S2", "program1 e", "312")]


def test_legend_keeps_citation_order_by_number() -> None:
    pac = "A ' fuente: S6\nB ' fuente: S2"
    refs = _resolve_references(_source_map(), pac)
    assert [sid for sid, _, _ in refs] == ["S2", "S6"]


def test_legend_falls_back_to_all_when_code_cites_nothing() -> None:
    """Sin citas no se deja el programa sin ninguna procedencia."""
    refs = _resolve_references(_source_map(), "PROGRAM p\nEND")
    assert len(refs) == 6


def test_legend_ignores_hallucinated_ids_not_in_the_map() -> None:
    """S9 no se recuperó: no puede resolverse y no debe inventarse."""
    pac = "A ' fuente: S2\nB ' fuente: S9"
    refs = _resolve_references(_source_map(), pac)
    assert [sid for sid, _, _ in refs] == ["S2"]


def test_legend_without_pac_code_returns_all_as_before() -> None:
    """Compatibilidad: sin el argumento, el comportamiento antiguo."""
    assert len(_resolve_references(_source_map())) == 6


# ── _prepend_source_legend ─────────────────────────────────────────


def test_prepended_legend_shows_only_the_cited_source() -> None:
    pac = "PROGRAM move_joints\n    DRIVEA (1, 45)    ' fuente: S2\nEND"
    refs = _resolve_references(_source_map(), pac)
    out = _prepend_source_legend(pac, _source_map(), refs)

    assert "' S2 = program1 e, pág. 312" in out
    # Las que no sustentan el código no aparecen:
    for ruido in ("S1 =", "S4 =", "S5 =", "S6 ="):
        assert ruido not in out
    assert out.endswith(pac)


def test_prepended_legend_matches_the_references_field() -> None:
    """La leyenda del archivo y el campo references no pueden discrepar.

    Recalcularla aquí sobre el código ya anotado contaría las propias líneas de
    la leyenda ("' S2 = …"), así que se pasa ya resuelta.
    """
    pac = "PROGRAM p\n    X    ' fuente: S2\nEND"
    refs = _resolve_references(_source_map(), pac)
    out = _prepend_source_legend(pac, _source_map(), refs)

    en_leyenda = {
        line.split("=")[0].strip("' ").strip()
        for line in out.split("\n")
        if line.startswith("' S")
    }
    assert en_leyenda == {sid for sid, _, _ in refs}
