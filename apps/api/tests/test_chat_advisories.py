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
