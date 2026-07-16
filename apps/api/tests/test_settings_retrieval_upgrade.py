"""Tests de la subida de top-k y del presupuesto de contexto.

Medido sobre las tres consultas reales que fallaron en WinCaps III: con top_k=6
llegaban 2-4 fragmentos útiles y el resto eran portadas, prefacios y folletos.
Con 12 llegan 5-7. Subir a 18 no aportó ninguno más y desbordaba el presupuesto.

El presupuesto sube con él porque _run_rag_phases descarta EN SILENCIO lo que no
cabe (`break`), así que 12 fragmentos (~15.500 chars en el peor caso medido) se
habrían recortado a ~9 sin avisar.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models.settings import SystemSetting
from src.services.settings.service import (
    DEFAULT_SETTINGS,
    seed_if_empty,
    update_setting,
    upgrade_retrieval_defaults,
)


def test_defaults_are_the_measured_values() -> None:
    assert DEFAULT_SETTINGS["rag_top_k_chunks"][0] == "12"
    assert DEFAULT_SETTINGS["rag_context_budget_chars"][0] == "16000"


def test_budget_can_hold_top_k_chunks() -> None:
    """El presupuesto debe dar cabida a top_k, o recuperar de más no sirve.

    Los chunks miden ~1000 chars de media más la cabecera [SX | manual — pág. N].
    Con 12 × ~1300 = ~15.500 en el peor caso medido, 16.000 deja margen.
    """
    top_k = int(DEFAULT_SETTINGS["rag_top_k_chunks"][0])
    budget = int(DEFAULT_SETTINGS["rag_context_budget_chars"][0])
    assert budget >= top_k * 1300


def test_upgrade_moves_settings_still_at_the_old_default(db_session: Session) -> None:
    db_session.add(SystemSetting(key="rag_top_k_chunks", value="6", description="x"))
    db_session.add(
        SystemSetting(key="rag_context_budget_chars", value="12000", description="x")
    )
    db_session.commit()

    cambiadas = upgrade_retrieval_defaults(db_session)

    assert set(cambiadas) == {"rag_top_k_chunks", "rag_context_budget_chars"}
    rows = {r.key: r.value for r in db_session.query(SystemSetting).all()}
    assert rows["rag_top_k_chunks"] == "12"
    assert rows["rag_context_budget_chars"] == "16000"


def test_upgrade_respects_a_deliberate_admin_value(db_session: Session) -> None:
    """Un valor elegido a propósito no debe cambiar tras un despliegue.

    Es un ajuste de la consola admin, no una regla: si alguien puso 8, sabrá por
    qué. Solo se toca lo que sigue en el default anterior.
    """
    seed_if_empty(db_session)
    update_setting(db_session, "rag_top_k_chunks", "8")

    cambiadas = upgrade_retrieval_defaults(db_session)

    assert "rag_top_k_chunks" not in cambiadas
    row = (
        db_session.query(SystemSetting).filter_by(key="rag_top_k_chunks").one()
    )
    assert row.value == "8"


def test_upgrade_is_idempotent(db_session: Session) -> None:
    seed_if_empty(db_session)  # ya siembra los valores nuevos
    assert upgrade_retrieval_defaults(db_session) == []


def test_upgrade_is_noop_when_rows_are_absent(db_session: Session) -> None:
    assert upgrade_retrieval_defaults(db_session) == []
