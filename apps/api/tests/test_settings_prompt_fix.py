"""Tests for the system_prompt_pac IO-assignment fix (default + DB migration)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models.settings import SystemSetting
from src.services.settings.service import (
    _DEFAULT_PAC_RULES,
    _LEGACY_IO_ASSIGN,
    fix_legacy_io_assignment_prompt,
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
