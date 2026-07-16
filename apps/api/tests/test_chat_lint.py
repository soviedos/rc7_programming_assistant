"""Tests for the deterministic post-generation PAC linter."""

from __future__ import annotations

from src.services.chat.service import _lint_pac_code


def test_lint_converts_io_assignment_statements() -> None:
    code = "IO[ioGripperOpen] = ON\nIO[ioGripperClose] = OFF"
    out, n = _lint_pac_code(code)
    assert out == "SET IO[ioGripperOpen]\nRESET IO[ioGripperClose]"
    assert n == 2


def test_lint_preserves_indent_and_inline_source_comment() -> None:
    code = "    IO[ioLamp] = ON    ' fuente: S2"
    out, n = _lint_pac_code(code)
    assert out == "    SET IO[ioLamp]    ' fuente: S2"
    assert n == 1


def test_lint_does_not_touch_conditions() -> None:
    code = (
        "    IF IO[ioReady] = ON THEN\n"
        "        WAIT IO[ioAck] = ON\n"
        "        IF IO[ioErr] = OFF THEN\n"
        "    END IF"
    )
    out, n = _lint_pac_code(code)
    assert out == code  # unchanged
    assert n == 0


def test_lint_mixed_program_counts_only_statements() -> None:
    code = (
        "PROGRAM p\n"
        "    TAKEARM\n"
        "    WAIT IO[ioStart] = ON\n"  # condition — keep
        "    IO[ioLamp] = ON    ' fuente: S1\n"  # statement — SET
        "    IF IO[ioErr] = OFF THEN\n"  # condition — keep
        "        IO[ioLamp] = OFF\n"  # statement — RESET (nested indent)
        "    END IF\n"
        "END"
    )
    out, n = _lint_pac_code(code)

    assert n == 2
    lines = out.split("\n")
    assert "    SET IO[ioLamp]    ' fuente: S1" in lines
    assert "        RESET IO[ioLamp]" in lines
    # conditions left intact
    assert "    WAIT IO[ioStart] = ON" in lines
    assert "    IF IO[ioErr] = OFF THEN" in lines


def test_lint_handles_no_spaces_and_trailing_whitespace() -> None:
    out, n = _lint_pac_code("IO[0]=ON")
    assert out == "SET IO[0]"
    assert n == 1
    out2, n2 = _lint_pac_code("IO[1] = OFF   ")  # trailing spaces, no comment
    assert out2 == "RESET IO[1]"
    assert n2 == 1


def test_lint_empty_code_is_noop() -> None:
    assert _lint_pac_code("") == ("", 0)


# ── MOVE J → MOVE P ────────────────────────────────────────────────


def test_lint_rewrites_invalid_interpolation_j_to_ptp() -> None:
    """J no es método de interpolación (válidos: P, L, C, S).

    WinCaps III lo rechaza con "Wrong interpolation method designated. Kw(J)".
    Para un movimiento articular el correcto es PTP, documentado como `MOVE P, J1`.
    """
    code = "    MOVE J, J[jTarget], S=50    ' fuente: S4"
    out, n = _lint_pac_code(code)
    assert out == "    MOVE P, J[jTarget], S=50    ' fuente: S4"
    assert n == 1


def test_lint_leaves_valid_interpolation_methods_untouched() -> None:
    """P, L, C y S son válidos: tocarlos rompería código correcto."""
    code = "MOVE P, J1, S=50\nMOVE L, @0 P1\nMOVE C, P1, @P P2\nMOVE S, 1"
    out, n = _lint_pac_code(code)
    assert out == code
    assert n == 0


def test_lint_does_not_rewrite_move_j_inside_a_comment() -> None:
    """Las reglas están ancladas a línea: un comentario no es una sentencia."""
    code = "' No usar MOVE J, es invalido\nMOVE P, J1    ' correcto"
    out, n = _lint_pac_code(code)
    assert out == code
    assert n == 0


# ── J[x] = J(...) → J[x] = (...) ───────────────────────────────────


def test_lint_removes_bogus_joint_constructor() -> None:
    """No existe constructor J(): el manual asigna con `J[0] = (10,20,…)`.

    WinCaps III lo rechaza con "Type J data op('(')".
    """
    code = "J[jTarget] = J(45.0, -30.0, 0.0, 0.0, 0.0, 0.0)"
    out, n = _lint_pac_code(code)
    assert out == "J[jTarget] = (45.0, -30.0, 0.0, 0.0, 0.0, 0.0)"
    assert n == 1


def test_lint_removes_bogus_joint_constructor_on_numbered_variable() -> None:
    code = "    J1 = J(45, -30, 0, 0, 0, 0)    ' fuente: S1"
    out, n = _lint_pac_code(code)
    assert out == "    J1 = (45, -30, 0, 0, 0, 0)    ' fuente: S1"
    assert n == 1


def test_lint_leaves_valid_joint_assignment_untouched() -> None:
    """La forma documentada ya es correcta: no debe tocarse."""
    code = "J[0] = (10,20,30,40,50,60)\nJ1 = (11,12,13,14,15,16)\nJ1 = J[I5*3]"
    out, n = _lint_pac_code(code)
    assert out == code
    assert n == 0


def test_lint_fixes_the_real_wincaps_failure() -> None:
    """El programa exacto que el sistema generó y WinCaps III rechazó (5 errores).

    Ambos defectos son reescrituras seguras verificadas contra el corpus: ni
    `MOVE J,` ni `= J(` aparecen una sola vez en los 11 manuales.
    """
    code = (
        "PROGRAM move_joints\n"
        "    TAKEARM\n"
        "    J[jTarget] = J(45.0, -30.0, 0.0, 0.0, 0.0, 0.0)\n"
        "    MOVE J, J[jTarget], S=50                   ' (fuente: S4)\n"
        "    GIVEARM\n"
        "END"
    )
    out, n = _lint_pac_code(code)
    assert n == 2
    assert "J[jTarget] = (45.0, -30.0, 0.0, 0.0, 0.0, 0.0)" in out
    assert "MOVE P, J[jTarget], S=50                   ' (fuente: S4)" in out
    assert "MOVE J," not in out
    assert "= J(" not in out
