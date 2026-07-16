"""Tests for level-2 PAC semantic advisories (read-only, no auto-fix)."""

from __future__ import annotations

from src.services.chat.service import _pac_advisories


def test_step_move_before_io_yields_one_advisory() -> None:
    code = "MOVE P, @P P[pPick]\nSET IO[ioGrip]"
    adv = _pac_advisories(code)
    assert len(adv) == 1
    assert adv[0].startswith("Línea 1:")
    assert "movimiento de paso" in adv[0]


def test_step_move_before_another_move_no_advisory() -> None:
    # The pass is legitimate when the next statement is another motion.
    code = "MOVE P, @P P[pPrePick]\nMOVE P, @0 P[pPick]"
    assert _pac_advisories(code) == []


def test_stop_designator_before_io_no_advisory() -> None:
    # @0 decelerates and stops at the target — actuating an output is fine.
    code = "MOVE P, @0 P[pPick]\nSET IO[ioGrip]"
    assert _pac_advisories(code) == []


def test_comments_and_blanks_between_do_not_break_detection() -> None:
    code = (
        "    MOVE P, @P P[pPick]    ' fuente: S1\n"
        "\n"
        "    ' baja el gripper sobre la pieza\n"
        "    SET IO[ioGrip]"
    )
    adv = _pac_advisories(code)
    assert len(adv) == 1
    assert adv[0].startswith("Línea 1:")


def test_positive_integer_step_designator_triggers_with_reset() -> None:
    code = "APPROACH P, @5 P[pPlace], 50\nRESET IO[ioGrip]"
    adv = _pac_advisories(code)
    assert len(adv) == 1
    assert adv[0].startswith("Línea 1:")


def test_e_designator_does_not_trigger() -> None:
    code = "MOVE P, @E P[pPick]\nSET IO[ioGrip]"
    assert _pac_advisories(code) == []


def test_line_number_is_one_based_within_program() -> None:
    code = (
        "PROGRAM p\n"  # 1
        "    TAKEARM\n"  # 2
        "    MOVE P, @P P[pPick]\n"  # 3  ← step motion
        "    SET IO[ioGrip]\n"  # 4
        "END"  # 5
    )
    adv = _pac_advisories(code)
    assert len(adv) == 1
    assert adv[0].startswith("Línea 3:")


def test_empty_code_returns_empty() -> None:
    assert _pac_advisories("") == []


# ── Varios PROGRAM en una respuesta ────────────────────────────────


def test_advises_when_response_defines_two_programs() -> None:
    """WinCaps III admite un PROGRAM por archivo.

    Caso real: una respuesta de multitarea (bg_prog + main_prog) pegada en un solo
    .pac falla con "Plural program names are defined" y "Wrong name" en el RUN.
    """
    code = (
        "' ARCHIVO: bg_prog.pac\n"
        "PROGRAM bg_prog\n"
        "    I[iStatus] = 1\n"
        "END\n"
        "\n"
        "' ARCHIVO: main_prog.pac\n"
        "PROGRAM main_prog\n"
        "    RUN bg_prog\n"
        "END"
    )
    avisos = _pac_advisories(code)

    assert len(avisos) == 1
    assert "más de un PROGRAM" in avisos[0]
    assert "bg_prog, main_prog" in avisos[0]
    assert "Línea 7" in avisos[0]  # se emite en la SEGUNDA declaración


def test_does_not_advise_for_a_single_program() -> None:
    code = "PROGRAM pro1\n    TAKEARM\n    GIVEARM\nEND"
    assert _pac_advisories(code) == []


def test_advises_only_once_for_three_programs() -> None:
    """Un aviso por respuesta, no uno por programa."""
    code = "PROGRAM a\nEND\nPROGRAM b\nEND\nPROGRAM c\nEND"
    avisos = [a for a in _pac_advisories(code) if "más de un PROGRAM" in a]
    assert len(avisos) == 1


def test_program_inside_a_comment_is_not_a_declaration() -> None:
    """Las reglas van ancladas a línea: un comentario no declara nada."""
    code = "PROGRAM pro1\n    ' PROGRAM otro  es solo un comentario\nEND"
    assert _pac_advisories(code) == []
