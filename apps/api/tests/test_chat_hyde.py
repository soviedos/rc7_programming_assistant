"""Tests para la temperatura propia de la fase HyDE.

La fase 1 (HyDE) no redacta nada para el usuario: su única salida alimenta el
embedding con el que se buscan los chunks. Compartir la temperatura de generación
(0.7) hacía que la misma pregunta recuperase documentación distinta en cada
ejecución. Medido sobre la consulta que falló en WinCaps III: con 0.7 solo 1 de 5
ejecuciones recuperaba la sección "12.1 Motion Control"; con 0.0, 4 de 4.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.services.chat.service import _load_chat_params
from src.services.settings.service import seed_if_empty, update_setting


def test_hyde_temperature_defaults_to_deterministic(db_session: Session) -> None:
    params = _load_chat_params(db_session)
    assert params.hyde_temperature == 0.0


def test_hyde_temperature_is_independent_from_generation(db_session: Session) -> None:
    """Son dos trabajos distintos: la fase 4 redacta, la fase 1 solo busca."""
    params = _load_chat_params(db_session)
    assert params.temperature == 0.7
    assert params.hyde_temperature == 0.0


def test_hyde_temperature_is_tunable_from_settings(db_session: Session) -> None:
    """Ajustable en caliente desde la consola admin, como el resto.

    seed_if_empty primero: update_setting solo actualiza filas existentes, y es
    el seed de arranque quien las inserta desde el catálogo.
    """
    seed_if_empty(db_session)
    assert update_setting(db_session, "hyde_temperature", "0.4") is not None

    params = _load_chat_params(db_session)
    assert params.hyde_temperature == 0.4
    # la temperatura de generación no se ve afectada
    assert params.temperature == 0.7
