"""System settings service — CRUD for admin-configurable parameters."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.settings import SystemSetting

# ── Default PAC syntax rules (seed value for system_prompt_pac) ────

_DEFAULT_PAC_RULES = """\
Cuando generes código PAC debes seguir ESTRICTAMENTE la sintaxis real del lenguaje PAC \
tal como aparece en los programas de Denso Wincaps III (Capítulo 9 del manual RC7).

ESTRUCTURA Y SINTAXIS REAL DE UN PROGRAMA PAC:

1. DIRECTIVAS DE PREPROCESADOR (opcionales, van antes de PROGRAM):
   #INCLUDE "dio_tab.h"   'Lee el archivo de macros de E/S digitales
   #INCLUDE "var_tab.h"   'Lee el archivo de macros de variables
   #DEFINE appLen  100    'Define una constante (nombre y valor son equivalentes)

2. DECLARACIÓN DEL PROGRAMA:
   PROGRAM pro1

3. CUERPO PRINCIPAL: instrucciones terminadas con END.

4. SUBRUTINAS: definidas DESPUÉS del END con el formato:
   *NombreSubrutina:
       <instrucciones>
   RETURN

REGLAS CRÍTICAS DE SINTAXIS (incumplirlas genera errores de compilación o comportamiento incorrecto):

- CONTROL DEL BRAZO: se obtiene con TAKEARM y se libera con GIVEARM (NO usar FREEARM).
- MOTORES: MOTOR ON activa los motores; MOTOR OFF los apaga. Se usan según el contexto; \
en programas modulares el control de motores puede estar en el programa principal o en rutinas de init.
- MOVIMIENTO:
    * Movimiento PTP (articular): MOVE P, P[pHome], S=50  (S= especifica % de velocidad interna)
    * Movimiento lineal relativo: MOVE P, @P P[pPick]  (@ indica relativo al punto actual)
    * JUMP para trayectorias articulares largas entre puntos alejados: JUMP P[pPrePick]
    * Los puntos se referencian como macros: P[pHome], P[pPick], P[pPlace], etc.
      (definidos en var_tab.h) o como P0, P1, P10, etc.
- VARIABLES:
    * Enteras:    I[iPartsId], I[iCount]  (macros de var_tab.h)
    * Reales:     F[fDelay], F[fSpeed]
    * Cadenas:    C[cMsg]
    * NO declarar variables locales con DIM salvo casos especiales; usar macros.
- E/S DIGITALES:
    * Las señales se nombran con macros: ioParts, ioPartsAck, ioGripperOpen, etc.
    * Para esperar entrada y activar salida: CALL dioWaitAndSet(ioIn, ioOut)
    * Para activar salida y esperar confirmación: CALL dioSetAndWait(ioOut, ioAck)
    * Para ACTIVAR una salida:    SET IO[ioGripperOpen]      (NUNCA IO[ioGripperOpen] = ON)
    * Para DESACTIVAR una salida: RESET IO[ioGripperOpen]     (NUNCA IO[ioGripperOpen] = OFF)
    * La forma IO[n] = ON / OFF SOLO es válida como condición en IF/WAIT.
- LLAMADAS:
    * Programa externo: CALL pro2  (sin asterisco)
    * Subrutina interna: GOSUB *PlacePartsA  (con asterisco, SIN dos puntos al llamar)
    * La DEFINICIÓN de la subrutina sí lleva dos puntos: *PlacePartsA:
- CONTROL DE FLUJO:
    * Condicional múltiple: SELECT CASE I[iPartsId]
                               CASE -1
                                   CALL dioSetAndWait(ioErrQR, ioErrQRAck)
                               CASE 1
                                   GOSUB *PlacePartsA
                               CASE 2, 3
                                   GOSUB *PlacePartsBC
                           END SELECT
- VELOCIDAD: SPEED 100 establece velocidad interna al 100%; también ACCEL y DECEL.
- COMENTARIOS: siempre inline al final de la línea con comilla simple: TAKEARM  'Obtiene semáforo del brazo
  NO usar bloques de comentarios con ' --- encabezado --- ni líneas de comentario solas salvo
  cuando sea necesario para aclarar lógica compleja.

Ejemplo de programa real correcto:
  #INCLUDE "dio_tab.h"                           'Lee macros de E/S
  #INCLUDE "var_tab.h"                           'Lee macros de variables
  #DEFINE appLen  100                            'Define longitud de aproximación

  PROGRAM pro1
      TAKEARM                                    'Obtiene semáforo del brazo
      MOVE P, P[pHome], S=50                     'Mueve a HOME al 50% de velocidad interna
      SPEED 100                                  'Establece velocidad al 100%
      CALL dioWaitAndSet(ioParts, ioPartsAck)    'Verifica suministro de piezas
      CALL pro2                                  'Lee el código QR
      SELECT CASE I[iPartsId]
          CASE -1
              CALL dioSetAndWait(ioErrQR, ioErrQRAck) 'Salida de error
          CASE 1
              GOSUB *PlacePartsA                 'Procesa pieza A
          CASE 2, 3
              GOSUB *PlacePartsBC                'Procesa piezas B y C
      END SELECT
      CALL dioSetAndWait(ioComplete, ioCompleteAck) 'Señal de fin de movimiento
      GIVEARM                                    'Libera semáforo del brazo
  END

ARCHIVOS DE INCLUDE — REGLA OBLIGATORIA:
Cuando el programa use #INCLUDE "dio_tab.h" o #INCLUDE "var_tab.h", DEBES generar \
el contenido de esos archivos en el mismo campo pac_code, usando este formato de separación:

' ================================================================
' ARCHIVO: dio_tab.h
' ================================================================
#DEFINE ioGripperOpen    0   'Salida: abrir gripper
#DEFINE ioGripperClose   1   'Salida: cerrar gripper
...(todas las señales usadas en el programa)

' ================================================================
' ARCHIVO: var_tab.h
' ================================================================
#DEFINE pHome     0   'Punto de posición HOME
#DEFINE pPick     1   'Punto de recogida
...(todos los puntos y variables usados en el programa)

' ================================================================
' ARCHIVO: <nombre_programa>.pac
' ================================================================
#INCLUDE "dio_tab.h"
#INCLUDE "var_tab.h"
PROGRAM <nombre>
...
END

Los tres bloques van en el mismo string pac_code, en ese orden. \
Cada #DEFINE debe incluir el número de señal/índice real y un comentario descriptivo. \
Las señales de E/S deben corresponder al perfil I/O configurado del robot.

RESTRICCIONES:
- Genera código PAC libremente usando las reglas de sintaxis de este prompt \
más el contexto de manuales. Componer secuencias lógicas (pick & place, \
inicialización, manejo de E/S) es parte de tu tarea aunque el manual no las \
muestre completas.
- NUNCA inventes números de página, códigos de error numéricos ni valores de \
temporización que no aparezcan en el contexto. Si un dato específico no está, \
usa un comentario indicando que debe configurarse ('ajustar según aplicación').
- El campo 'references' debe contener SOLO los IDs de fuente [SX] del CONTEXTO que \
realmente usaste (p. ej. ["S1","S3"]), o [] si no usaste ninguna fuente. NUNCA inventes \
IDs que no aparezcan en el CONTEXTO. Cada instrucción o bloque PAC tomado de una fuente debe \
llevar al final un comentario con su ID, p. ej.: MOVE P, P1    ' fuente: S2
- Los identificadores de fuente (S1, S2, …) son etiquetas de trazabilidad asignadas por el \
sistema y se le muestran al usuario como una leyenda junto a la respuesta. NUNCA inventes ni \
expliques a qué manual corresponde un SX: no tienes acceso al mapeo de una respuesta anterior. \
Si el usuario pregunta qué significa un SX, indícale que consulte la leyenda de fuentes mostrada \
con esa respuesta; no adivines.

Reglas adicionales:
1. NUNCA omitas el PROGRAM ni el END.
2. Usa GIVEARM (no FREEARM) para liberar el brazo.
3. Usa macros para puntos y variables (P[pHome], I[iCount]) en lugar de literales P0, I[00].
4. Adapta las E/S al perfil I/O del robot indicado en la configuración.

Para troubleshooting: diagnostica paso a paso. Si el contexto incluye el código \
de error o la sección del manual, cítalos; si no, explica el diagnóstico general.\
"""

# ── Default settings catalogue ─────────────────────────────────────
# Each entry: key → (default_value, human-readable description)

DEFAULT_SETTINGS: dict[str, tuple[str, str]] = {
    "gemini_temperature": (
        "0.7",
        "Temperatura de generación de Gemini (0.0 – 1.0)",
    ),
    "gemini_max_tokens": (
        "8192",
        "Límite de tokens de salida para Gemini",
    ),
    "gemini_timeout_seconds": (
        "300",
        "Tiempo máximo de espera para llamadas a Gemini (segundos)",
    ),
    "rag_top_k_chunks": (
        "6",
        "Número de fragmentos RAG recuperados por consulta",
    ),
    "rag_context_budget_chars": (
        "12000",
        "Presupuesto de caracteres para el contexto RAG",
    ),
    "rag_candidate_pool": (
        "50",
        "Vecinos recuperados de pgvector antes del re-rank por hardware/categoría",
    ),
    "system_prompt_pac": (
        _DEFAULT_PAC_RULES,
        "Reglas de sintaxis PAC incluidas en el prompt del sistema",
    ),
    "history_max_entries": (
        "50",
        "Máximo de entradas de historial de chat por usuario",
    ),
}


# ── Read helpers ────────────────────────────────────────────────────


def get_setting(db: Session, key: str) -> SystemSetting | None:
    """Return the SystemSetting row for *key*, or None if not found."""
    return db.scalar(select(SystemSetting).where(SystemSetting.key == key))


def get_setting_value(db: Session, key: str, fallback: str) -> str:
    """Return the string value for *key*, or *fallback* on any failure."""
    try:
        row = get_setting(db, key)
        if row is not None:
            return row.value
    except Exception:
        pass
    return fallback


def get_all_settings(db: Session) -> list[SystemSetting]:
    """Return all settings ordered by key."""
    return list(db.scalars(select(SystemSetting).order_by(SystemSetting.key)))


# ── Write helpers ───────────────────────────────────────────────────


def update_setting(
    db: Session,
    key: str,
    value: str,
    updated_by: int | None = None,
) -> SystemSetting | None:
    """Update an existing setting. Returns None if the key does not exist."""
    row = get_setting(db, key)
    if row is None:
        return None
    row.value = value
    row.updated_by = updated_by
    db.commit()
    db.refresh(row)
    return row


def reset_to_defaults(db: Session) -> None:
    """Upsert all default values, restoring any customised settings."""
    for key, (value, description) in DEFAULT_SETTINGS.items():
        row = get_setting(db, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value, description=description))
        else:
            row.value = value
    db.commit()


def seed_if_empty(db: Session) -> None:
    """Insert default settings only for keys that don't exist yet."""
    for key, (value, description) in DEFAULT_SETTINGS.items():
        existing = get_setting(db, key)
        if existing is None:
            db.add(SystemSetting(key=key, value=value, description=description))
    db.commit()


# ── Idempotent prompt migrations ───────────────────────────────────
# WinCaps III rejects `IO[n] = ON/OFF` as an assignment ("Instruction not
# conform to format. Kw(IO)"); the correct form is SET/RESET. The legacy line
# below was once recommended by the default prompt and may persist in saved
# settings, which take precedence over the (now-fixed) code default.

_LEGACY_IO_ASSIGN = (
    "Asignación directa: IO[ioGripperOpen] = ON  o  IO[ioGripperOpen] = OFF"
)
# Replaces ONLY the legacy substring, keeping the leading "    * " bullet that
# precedes it; the result matches the corrected code default verbatim.
_FIXED_IO_ASSIGN = (
    "Para ACTIVAR una salida:    SET IO[ioGripperOpen]      (NUNCA IO[ioGripperOpen] = ON)\n"
    "    * Para DESACTIVAR una salida: RESET IO[ioGripperOpen]     (NUNCA IO[ioGripperOpen] = OFF)\n"
    "    * La forma IO[n] = ON / OFF SOLO es válida como condición en IF/WAIT."
)


def fix_legacy_io_assignment_prompt(db: Session) -> bool:
    """Replace the legacy invalid IO-assignment line in a saved system_prompt_pac.

    Substring replacement only (preserves any other user customisation), idempotent
    (no-op once the legacy substring is gone), and safe when the row is absent.
    Returns ``True`` only when a row was actually updated.
    """
    row = get_setting(db, "system_prompt_pac")
    if row is None or _LEGACY_IO_ASSIGN not in row.value:
        return False
    row.value = row.value.replace(_LEGACY_IO_ASSIGN, _FIXED_IO_ASSIGN)
    db.commit()
    return True
