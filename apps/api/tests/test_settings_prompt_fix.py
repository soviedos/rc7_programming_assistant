"""Tests for the system_prompt_pac IO-assignment fix (default + DB migration)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models.settings import SystemSetting
from src.services.settings.service import (
    _DEFAULT_PAC_RULES,
    _LEGACY_IO_ASSIGN,
    _LEGACY_MOVE_BLOCK,
    _ONE_PROGRAM_RULE,
    fix_legacy_io_assignment_prompt,
    fix_legacy_move_prompt,
    fix_missing_one_program_rule_prompt,
)


def test_default_prompt_uses_set_reset_not_assignment() -> None:
    """The default no longer recommends the invalid IO[n] = ON/OFF assignment."""
    assert _LEGACY_IO_ASSIGN not in _DEFAULT_PAC_RULES
    assert "Asignación directa: IO[ioGripperOpen] = ON" not in _DEFAULT_PAC_RULES
    # Correct forms are now taught:
    assert "SET IO[ioGripperOpen]" in _DEFAULT_PAC_RULES
    assert "RESET IO[ioGripperOpen]" in _DEFAULT_PAC_RULES
    # The = ON/OFF form is mentioned only as a prohibition / condition note.
    assert "SOLO es válida como condición" in _DEFAULT_PAC_RULES


def _seed_prompt(db: Session, value: str) -> None:
    db.add(SystemSetting(key="system_prompt_pac", value=value, description="x"))
    db.commit()


def test_fix_transforms_legacy_line_and_preserves_customization(
    db_session: Session,
) -> None:
    custom = (
        "REGLAS PERSONALIZADAS DEL USUARIO.\n"
        "- E/S DIGITALES:\n"
        "    * Asignación directa: IO[ioGripperOpen] = ON  o  IO[ioGripperOpen] = OFF\n"
        "- FIN PERSONALIZADO."
    )
    _seed_prompt(db_session, custom)

    changed = fix_legacy_io_assignment_prompt(db_session)
    assert changed is True

    row = db_session.query(SystemSetting).filter_by(key="system_prompt_pac").one()
    assert _LEGACY_IO_ASSIGN not in row.value
    assert "    * Para ACTIVAR una salida:" in row.value
    assert "SET IO[ioGripperOpen]" in row.value
    assert "RESET IO[ioGripperOpen]" in row.value
    # Surrounding user customization is preserved (substring replace, not overwrite).
    assert row.value.startswith("REGLAS PERSONALIZADAS DEL USUARIO.")
    assert row.value.endswith("- FIN PERSONALIZADO.")


def test_fix_is_idempotent(db_session: Session) -> None:
    _seed_prompt(
        db_session,
        "x\n    * Asignación directa: IO[ioGripperOpen] = ON  o  IO[ioGripperOpen] = OFF\ny",
    )

    assert fix_legacy_io_assignment_prompt(db_session) is True
    row = db_session.query(SystemSetting).filter_by(key="system_prompt_pac").one()
    after_first = row.value

    # Second run finds no legacy substring → no-op, value unchanged.
    assert fix_legacy_io_assignment_prompt(db_session) is False
    db_session.refresh(row)
    assert row.value == after_first


def test_fix_is_safe_when_row_missing(db_session: Session) -> None:
    assert fix_legacy_io_assignment_prompt(db_session) is False


# ── Bloque de movimiento: MOVE/@ falsos y DRIVE/DRIVEA ausentes ─────


def test_default_prompt_no_longer_mislabels_move_p_as_linear() -> None:
    """El prompt llamaba "lineal" a MOVE P y decía que "@" era relativo.

    MOVE P es PTP (lo dice el propio prompt una línea antes); lineal es MOVE L.
    Y @P/@0/@E son pass/end/encoder-check motion: ningún manual liga "@" con
    movimiento relativo, que se expresa con aritmética sobre la posición actual.
    """
    assert "Movimiento lineal relativo: MOVE P" not in _DEFAULT_PAC_RULES
    assert "@ indica relativo al punto actual" not in _DEFAULT_PAC_RULES
    # Ahora enseña lo correcto:
    assert "Lineal: MOVE L," in _DEFAULT_PAC_RULES
    assert "@P = pass motion" in _DEFAULT_PAC_RULES
    assert "MOVE P, @P P0+(0, 0, -70)H" in _DEFAULT_PAC_RULES


def test_default_prompt_teaches_per_axis_motion() -> None:
    """La ausencia de DRIVE/DRIVEA es lo que llevó al modelo a inventar MOVE J."""
    assert "DRIVEA (1, 45), (2, -30)" in _DEFAULT_PAC_RULES
    assert "DRIVE (1, 45)" in _DEFAULT_PAC_RULES
    # y avisa de las dos invenciones que WinCaps III rechazó:
    assert 'NO existe "MOVE J"' in _DEFAULT_PAC_RULES
    assert "NO existe el constructor J(...)" in _DEFAULT_PAC_RULES
    # los métodos válidos, explícitos
    assert "P = PTP (articular)   L = lineal   C = circular   S = curva libre" in (
        _DEFAULT_PAC_RULES
    )


def test_move_fix_upgrades_saved_prompt_and_preserves_customization(
    db_session: Session,
) -> None:
    custom = (
        "REGLAS PERSONALIZADAS DEL USUARIO.\n"
        + _LEGACY_MOVE_BLOCK
        + "    * JUMP para trayectorias articulares largas: JUMP P[pPrePick]\n"
        + "- VARIABLES:\n"
        + "- FIN PERSONALIZADO."
    )
    _seed_prompt(db_session, custom)

    assert fix_legacy_move_prompt(db_session) is True

    row = db_session.query(SystemSetting).filter_by(key="system_prompt_pac").one()
    assert "Movimiento lineal relativo: MOVE P" not in row.value
    assert "@ indica relativo al punto actual" not in row.value
    assert "DRIVEA (1, 45), (2, -30)" in row.value
    # El bloque articular se inserta ANTES de - VARIABLES:, no al final.
    assert row.value.index("DRIVEA") < row.value.index("- VARIABLES:")
    # La personalización del usuario sobrevive (reemplazo de subcadena).
    assert row.value.startswith("REGLAS PERSONALIZADAS DEL USUARIO.")
    assert row.value.endswith("- FIN PERSONALIZADO.")
    # Las líneas correctas del bloque original se conservan.
    assert "JUMP P[pPrePick]" in row.value


def test_move_fix_is_idempotent(db_session: Session) -> None:
    _seed_prompt(db_session, _LEGACY_MOVE_BLOCK + "- VARIABLES:\n")

    assert fix_legacy_move_prompt(db_session) is True
    row = db_session.query(SystemSetting).filter_by(key="system_prompt_pac").one()
    primera = row.value

    # Segunda pasada: ya está al día, no debe tocar nada ni duplicar el bloque.
    assert fix_legacy_move_prompt(db_session) is False
    db_session.refresh(row)
    assert row.value == primera
    assert row.value.count("DRIVEA (1, 45), (2, -30)") == 1


def test_move_fix_is_noop_when_row_absent(db_session: Session) -> None:
    assert fix_legacy_move_prompt(db_session) is False


# ── Regla "un PROGRAM por archivo" ─────────────────────────────────


def test_default_prompt_teaches_one_program_per_file() -> None:
    """Sin esta regla, una respuesta de multitarea pegada en un solo archivo
    falla con "Plural program names are defined" y "Wrong name" en el RUN."""
    assert "UN PROGRAM POR ARCHIVO" in _DEFAULT_PAC_RULES
    assert "Plural program names are defined" in _DEFAULT_PAC_RULES
    # y exige avisarlo en el summary, que es lo que el usuario lee
    assert "DI EN EL SUMMARY" in _DEFAULT_PAC_RULES


def test_one_program_rule_is_derived_from_the_default_verbatim() -> None:
    """El texto que inserta la migración sale del propio default, no de una copia.

    Es la garantía de que seed_if_empty y la migración no pueden divergir: una
    constante copiada a mano sí lo haría en cuanto se editara el default.
    """
    assert _ONE_PROGRAM_RULE in _DEFAULT_PAC_RULES
    assert _ONE_PROGRAM_RULE.startswith("UN PROGRAM POR ARCHIVO")


def test_one_program_fix_upgrades_an_old_saved_prompt(db_session: Session) -> None:
    viejo = _DEFAULT_PAC_RULES.replace(_ONE_PROGRAM_RULE, "")
    _seed_prompt(db_session, viejo)
    assert "UN PROGRAM POR ARCHIVO" not in viejo

    assert fix_missing_one_program_rule_prompt(db_session) is True

    row = db_session.query(SystemSetting).filter_by(key="system_prompt_pac").one()
    # Converge exactamente al default: la migración no deja un prompt "parecido".
    assert row.value == _DEFAULT_PAC_RULES


def test_one_program_fix_is_idempotent(db_session: Session) -> None:
    _seed_prompt(db_session, _DEFAULT_PAC_RULES)
    assert fix_missing_one_program_rule_prompt(db_session) is False

    row = db_session.query(SystemSetting).filter_by(key="system_prompt_pac").one()
    assert row.value.count("UN PROGRAM POR ARCHIVO") == 1


def test_one_program_fix_is_noop_without_anchor(db_session: Session) -> None:
    """Un prompt personalizado sin la sección RESTRICCIONES: no se toca."""
    _seed_prompt(db_session, "PROMPT TOTALMENTE PERSONALIZADO SIN ANCLA")
    assert fix_missing_one_program_rule_prompt(db_session) is False
