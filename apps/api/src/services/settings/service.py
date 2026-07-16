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
- MOVIMIENTO A UN PUNTO (MOVE <método>, <destino>):
    * El método de interpolación es la letra tras MOVE y SOLO puede ser:
        P = PTP (articular)   L = lineal   C = circular   S = curva libre
      NO existe "MOVE J": designar J da el error "Wrong interpolation method".
    * PTP: MOVE P, P[pHome], S=50   (S= especifica % de velocidad interna)
    * Lineal: MOVE L, P[pPick], S=20
    * @P / @0 / @E NO significan "relativo": eligen cómo se transita el punto.
      @P = pass motion (pasa de largo sin detenerse), @0 = end motion (se detiene
      al alcanzar el valor de comando), @E = espera confirmación del encoder.
      Ej.: MOVE L, @P P1  encadena sin parar; MOVE L, @0 P2 se detiene en P2.
    * Movimiento RELATIVO: aritmética sobre la posición actual, no con @.
      Ej.: MOVE P, @P P0+(0, 0, -70)H   (P0 es la posición actual)
    * JUMP para trayectorias articulares largas entre puntos alejados: JUMP P[pPrePick]
    * Los puntos se referencian como macros: P[pHome], P[pPick], P[pPlace], etc.
      (definidos en var_tab.h) o como P0, P1, P10, etc.
- MOVIMIENTO POR ÁNGULO DE EJE (cuando se pide mover una articulación a N grados):
    * ABSOLUTO — "mueve el eje 1 A 45 grados":   DRIVEA (1, 45)
      Varios ejes a la vez:                      DRIVEA (1, 45), (2, -30)
    * RELATIVO — "gira el eje 1 45 grados MÁS":  DRIVE (1, 45)
      Elegir mal entre ambos COMPILA igual y mueve el robot a otro sitio: DRIVEA
      va a un ángulo, DRIVE suma ese ángulo a la posición actual.
    * Todos los ejes de una vez, con una variable tipo J:
        J1 = (45, -30, 0, 0, 0, 0)   'también J[0] = (45, -30, 0, 0, 0, 0)
        MOVE P, J1, S=50             'PTP hasta la pose articular
      NO existe el constructor J(...): "J1 = J(45, ...)" da "Type J data op('(')".
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

UN PROGRAM POR ARCHIVO — REGLA OBLIGATORIA:
Un archivo .pac admite EXACTAMENTE una declaración PROGRAM. Dos en el mismo archivo \
fallan al compilar con "Plural program names are defined", y el RUN que invoque al \
segundo falla con "Wrong name" porque no existe como archivo propio.
Si la tarea necesita varios programas (p. ej. multitarea con RUN), emite un bloque \
' ARCHIVO: <nombre>.pac por cada uno — y DI EN EL SUMMARY, de forma explícita, que \
cada bloque debe guardarse como un archivo separado del proyecto WinCaps. Quien pegue \
todos los bloques en un solo archivo obtendrá errores de compilación.

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
    "hyde_temperature": (
        "0.0",
        "Temperatura de la fase HyDE (0.0 – 1.0). Su salida solo alimenta la "
        "búsqueda, no se muestra: subirla vuelve la recuperación inestable",
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


# ── system_prompt_pac: movimiento (bloque legacy) ──────────────────
#
# El bloque de movimiento del prompt afirmaba dos cosas falsas en una línea:
# llamaba "lineal" a MOVE P (que es PTP, como decía la línea anterior) y decía
# que "@ indica relativo al punto actual" — @P/@0/@E son pass/end/encoder-check
# motion, y el relativo se expresa con aritmética (P0+(0,0,-70)). Además no
# mencionaba el movimiento por ángulo de eje, así que el modelo inventaba
# "MOVE J" y "J(...)" cuando se le pedía mover una articulación a N grados.

_LEGACY_MOVE_BLOCK = (
    "- MOVIMIENTO:\n"
    "    * Movimiento PTP (articular): MOVE P, P[pHome], S=50  "
    "(S= especifica % de velocidad interna)\n"
    "    * Movimiento lineal relativo: MOVE P, @P P[pPick]  "
    "(@ indica relativo al punto actual)\n"
)

# Reemplaza SOLO la cabecera y las dos primeras viñetas del bloque: las líneas
# siguientes (JUMP, macros de punto) eran correctas y se conservan tal cual.
_FIXED_MOVE_BLOCK = (
    "- MOVIMIENTO A UN PUNTO (MOVE <método>, <destino>):\n"
    "    * El método de interpolación es la letra tras MOVE y SOLO puede ser:\n"
    "        P = PTP (articular)   L = lineal   C = circular   S = curva libre\n"
    '      NO existe "MOVE J": designar J da el error "Wrong interpolation method".\n'
    "    * PTP: MOVE P, P[pHome], S=50   (S= especifica % de velocidad interna)\n"
    "    * Lineal: MOVE L, P[pPick], S=20\n"
    '    * @P / @0 / @E NO significan "relativo": eligen cómo se transita el punto.\n'
    "      @P = pass motion (pasa de largo sin detenerse), @0 = end motion (se detiene\n"
    "      al alcanzar el valor de comando), @E = espera confirmación del encoder.\n"
    "      Ej.: MOVE L, @P P1  encadena sin parar; MOVE L, @0 P2 se detiene en P2.\n"
    "    * Movimiento RELATIVO: aritmética sobre la posición actual, no con @.\n"
    "      Ej.: MOVE P, @P P0+(0, 0, -70)H   (P0 es la posición actual)\n"
)

# Se inserta antes de "- VARIABLES:", que cierra el bloque de movimiento.
_VARIABLES_ANCHOR = "- VARIABLES:"
_JOINT_MOVE_BLOCK = (
    "- MOVIMIENTO POR ÁNGULO DE EJE (cuando se pide mover una articulación a N grados):\n"
    '    * ABSOLUTO — "mueve el eje 1 A 45 grados":   DRIVEA (1, 45)\n'
    "      Varios ejes a la vez:                      DRIVEA (1, 45), (2, -30)\n"
    '    * RELATIVO — "gira el eje 1 45 grados MÁS":  DRIVE (1, 45)\n'
    "      Elegir mal entre ambos COMPILA igual y mueve el robot a otro sitio: DRIVEA\n"
    "      va a un ángulo, DRIVE suma ese ángulo a la posición actual.\n"
    "    * Todos los ejes de una vez, con una variable tipo J:\n"
    "        J1 = (45, -30, 0, 0, 0, 0)   'también J[0] = (45, -30, 0, 0, 0, 0)\n"
    "        MOVE P, J1, S=50             'PTP hasta la pose articular\n"
    '      NO existe el constructor J(...): "J1 = J(45, ...)" da "Type J data op(\'(\')".\n'
)


# ── system_prompt_pac: regla "un PROGRAM por archivo" ─────────────
#
# WinCaps III falla con "Plural program names are defined" si un .pac declara
# dos PROGRAM, y con "Wrong name" en el RUN que invoque al segundo. El prompt
# pedía los bloques ' ARCHIVO: en un solo pac_code sin advertir que cada uno va
# a un archivo distinto del proyecto.

_RESTRICTIONS_ANCHOR = "RESTRICCIONES:"

# Derivado del propio default en vez de copiado: así el texto que inserta la
# migración y el que siembra seed_if_empty NO PUEDEN divergir.
_ONE_PROGRAM_RULE = _DEFAULT_PAC_RULES[
    _DEFAULT_PAC_RULES.index("UN PROGRAM POR ARCHIVO") : _DEFAULT_PAC_RULES.index(
        _RESTRICTIONS_ANCHOR
    )
]


def fix_missing_one_program_rule_prompt(db: Session) -> bool:
    """Añade la regla "un PROGRAM por archivo" a un system_prompt_pac guardado.

    El prompt mandaba emitir los bloques ' ARCHIVO: en un único pac_code pero
    nunca decía que cada uno debe guardarse aparte. Al pedir multitarea el modelo
    emitía dos PROGRAM y quien los pegaba juntos chocaba con "Plural program names
    are defined". Inserta el bloque antes de RESTRICCIONES:, que lo sigue.

    Idempotente y no-op si la fila no existe o el ancla no está.
    """
    row = get_setting(db, "system_prompt_pac")
    if row is None:
        return False
    if _ONE_PROGRAM_RULE in row.value or _RESTRICTIONS_ANCHOR not in row.value:
        return False

    row.value = row.value.replace(
        _RESTRICTIONS_ANCHOR, _ONE_PROGRAM_RULE + _RESTRICTIONS_ANCHOR, 1
    )
    db.commit()
    return True


def fix_legacy_move_prompt(db: Session) -> bool:
    """Corrige el bloque de movimiento en un system_prompt_pac ya guardado.

    Dos reemplazos de subcadena, ambos idempotentes y aplicables por separado:
    corregir las afirmaciones falsas sobre MOVE/@, e insertar el bloque de
    movimiento por ángulo de eje. Preserva cualquier otra personalización y es
    no-op si la fila no existe o ya está al día.

    Devuelve ``True`` solo si se actualizó algo.
    """
    row = get_setting(db, "system_prompt_pac")
    if row is None:
        return False

    value = row.value
    if _LEGACY_MOVE_BLOCK in value:
        value = value.replace(_LEGACY_MOVE_BLOCK, _FIXED_MOVE_BLOCK)
    if _JOINT_MOVE_BLOCK not in value and _VARIABLES_ANCHOR in value:
        value = value.replace(
            _VARIABLES_ANCHOR, _JOINT_MOVE_BLOCK + _VARIABLES_ANCHOR, 1
        )

    if value == row.value:
        return False
    row.value = value
    db.commit()
    return True
