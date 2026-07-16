"""Tests de la subida de top-k y del presupuesto de contexto.

Medido sobre las tres consultas reales que fallaron en WinCaps III, POR EL CAMINO
REAL (HyDE → embedding de prompt+hipótesis → retrieve), contando los fragmentos
que traen código PAC ejecutable en vez de portadas, prefacios y folletos:

    consulta        top6   top12   top18   top24   top30
    VP-6242            1       2       3       4       6
    joint 1 a 45°      6      12      15      17      21
    multitarea         6      10      12      14      18

Medir embebiendo la consulta cruda da otra cosa (VP-6242 se queda en 1 útil en
todos los niveles): sin HyDE esa consulta recupera fichas de producto, no código.

El presupuesto sube con top-k porque _run_rag_phases descarta EN SILENCIO lo que
no cabe (`break`), así que 24 fragmentos (~26.000 chars en el peor caso medido)
con 24.000 se habrían recortado sin avisar: recuperar de más no serviría de nada.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.db.models.settings import SystemSetting
from src.services.settings.service import (
    DEFAULT_SETTINGS,
    seed_if_empty,
    update_setting,
    upgrade_retrieval_defaults,
)


def test_defaults_are_the_measured_values() -> None:
    assert DEFAULT_SETTINGS["rag_top_k_chunks"][0] == "24"
    assert DEFAULT_SETTINGS["rag_context_budget_chars"][0] == "32000"


def test_every_description_fits_the_column() -> None:
    """description es VARCHAR(255): una más larga revienta seed_if_empty.

    Y no falla suave: initialize_database propaga el DataError y la API no
    arranca. Se descubrió al escribir una descripción de 284 chars.
    """
    limite = SystemSetting.__table__.c.description.type.length
    largas = {k: len(d) for k, (_v, d) in DEFAULT_SETTINGS.items() if len(d) > limite}
    assert not largas, f"descripciones que exceden VARCHAR({limite}): {largas}"


# Peor caso medido con la cabecera [SX | manual — pág. N] incluida, que es lo que
# de verdad consume presupuesto: 25.885 chars / 24 fragmentos ≈ 1.080 por fragmento.
# Se redondea a 1.300 para dejar margen: el tamaño varía con el manual que toque.
_CHARS_POR_FRAGMENTO = 1300


def test_budget_can_hold_top_k_chunks() -> None:
    """El presupuesto debe dar cabida a top_k, o recuperar de más no sirve.

    Es el invariante que ata las dos claves: subir una sin la otra hace que la
    fase 3 recorte en silencio y el trabajo extra de recuperación se tire.
    """
    top_k = int(DEFAULT_SETTINGS["rag_top_k_chunks"][0])
    budget = int(DEFAULT_SETTINGS["rag_context_budget_chars"][0])
    assert budget >= top_k * _CHARS_POR_FRAGMENTO


def test_upgrade_moves_settings_still_at_the_old_default(db_session: Session) -> None:
    db_session.add(SystemSetting(key="rag_top_k_chunks", value="6", description="x"))
    db_session.add(
        SystemSetting(key="rag_context_budget_chars", value="12000", description="x")
    )
    db_session.commit()

    cambiadas = upgrade_retrieval_defaults(db_session)

    assert set(cambiadas) == {"rag_top_k_chunks", "rag_context_budget_chars"}
    rows = {r.key: r.value for r in db_session.query(SystemSetting).all()}
    assert rows["rag_top_k_chunks"] == "24"
    assert rows["rag_context_budget_chars"] == "32000"


@pytest.mark.parametrize("viejo", ["6", "12", "18"])
def test_upgrade_moves_every_default_that_has_ever_existed(
    db_session: Session, viejo: str
) -> None:
    """Una instalación puede venir del default original (6) o de un intermedio.

    Todas deben converger: si solo se contemplara el original, quien ya hubiera
    desplegado una versión intermedia se quedaría ahí para siempre, porque
    seed_if_empty nunca pisa un valor existente.
    """
    db_session.add(
        SystemSetting(key="rag_top_k_chunks", value=viejo, description="x")
    )
    db_session.commit()

    assert "rag_top_k_chunks" in upgrade_retrieval_defaults(db_session)
    row = db_session.query(SystemSetting).filter_by(key="rag_top_k_chunks").one()
    assert row.value == "24"


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
