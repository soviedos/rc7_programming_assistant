"""Tests de la subida de top-k y del presupuesto de contexto.

Medido sobre las tres consultas reales que fallaron en WinCaps III, contando los
fragmentos que traen código PAC utilizable: con top_k=6 llegaban 2-4 y el resto
eran portadas, prefacios y folletos; con 12 llegan 7-9; con 18, 9-15.

El presupuesto sube con él porque _run_rag_phases descarta EN SILENCIO lo que no
cabe (`break`), así que 18 fragmentos (~23.000 chars en el peor caso medido) se
habrían recortado a ~12 sin avisar: recuperar de más no habría servido de nada.
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
    assert DEFAULT_SETTINGS["rag_top_k_chunks"][0] == "18"
    assert DEFAULT_SETTINGS["rag_context_budget_chars"][0] == "24000"


def test_every_description_fits_the_column() -> None:
    """description es VARCHAR(255): una más larga revienta seed_if_empty.

    Y no falla suave: initialize_database propaga el DataError y la API no
    arranca. Se descubrió al escribir una descripción de 284 chars.
    """
    limite = SystemSetting.__table__.c.description.type.length
    largas = {k: len(d) for k, (_v, d) in DEFAULT_SETTINGS.items() if len(d) > limite}
    assert not largas, f"descripciones que exceden VARCHAR({limite}): {largas}"


def test_budget_can_hold_top_k_chunks() -> None:
    """El presupuesto debe dar cabida a top_k, o recuperar de más no sirve.

    Los chunks miden ~1000 chars de media más la cabecera [SX | manual — pág. N].
    Con 18 × ~1300 = ~23.400 en el peor caso medido, 24.000 deja margen.
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
    assert rows["rag_top_k_chunks"] == "18"
    assert rows["rag_context_budget_chars"] == "24000"


def test_upgrade_also_moves_the_intermediate_default(db_session: Session) -> None:
    """Una instalación puede venir del default original (6) o del intermedio (12).

    Ambas deben converger: si solo se contemplara el original, quien ya hubiera
    desplegado la versión con 12 se quedaría ahí para siempre.
    """
    db_session.add(SystemSetting(key="rag_top_k_chunks", value="12", description="x"))
    db_session.commit()

    assert "rag_top_k_chunks" in upgrade_retrieval_defaults(db_session)
    row = db_session.query(SystemSetting).filter_by(key="rag_top_k_chunks").one()
    assert row.value == "18"


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
