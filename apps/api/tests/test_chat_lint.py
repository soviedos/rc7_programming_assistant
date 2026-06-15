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
