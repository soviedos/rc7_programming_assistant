# Módulo Settings — Parámetros Configurables

El módulo `settings` permite ajustar los parámetros del pipeline RAG y de Gemini en caliente,
sin reiniciar el stack. Los valores se almacenan en la tabla `system_settings` de PostgreSQL
y se leen en cada request.

---

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/admin/settings` | Lista todos los parámetros con sus valores actuales |
| `GET` | `/api/v1/admin/settings/{key}` | Obtiene el valor de un parámetro específico |
| `PUT` | `/api/v1/admin/settings/{key}` | Actualiza el valor de un parámetro |
| `POST` | `/api/v1/admin/settings/reset` | Restaura todos los parámetros a sus valores por defecto |

Todos los endpoints requieren rol `admin`.

**Audit:** `PUT` genera evento `SETTING_UPDATED`; `POST /reset` genera evento `SETTING_RESET`.

---

## Parámetros disponibles

| Clave | Tipo | Default | Descripción | Efecto en el pipeline |
|---|---|---|---|---|
| `gemini_temperature` | `float` | `0.7` | Temperatura de generación Gemini (0.0–1.0) | Controla la aleatoriedad de las respuestas: 0.0 = determinista, 1.0 = más creativo. **Solo afecta a la Fase 4** |
| `hyde_temperature` | `float` | `0.0` | Temperatura de la Fase 1 (HyDE) | Tiene su propia clave porque su salida **no se muestra**: solo alimenta el embedding de búsqueda. Con la de generación (0.7) cada ejecución producía una hipótesis distinta y recuperaba fragmentos distintos para la misma pregunta |
| `gemini_max_tokens` | `int` | `8192` | Límite de tokens de salida en Gemini (Phase 4 fuerza `response_mime_type=application/json` para emitir JSON puro) | Respuestas truncadas si el modelo alcanza el límite; con Gemini 3.5 Flash se recomienda ≥ 8192 para código PAC completo |
| `gemini_timeout_seconds` | `int` | `300` | Timeout (segundos) de cada llamada a Gemini. **Ahora se lee** y se propaga al cliente en las 4 fases (fallback al env `GEMINI_TIMEOUT_SECONDS`). | Requests más largos fallan con timeout |
| `rag_top_k_chunks` | `int` | `24` | Chunks finales (tras re-rank) enviados como contexto | Ver [la medición](#cuánto-aporta-subir-top-k) abajo. Con 24 el contexto ronda los 7k tokens — 0,7 % de la ventana de Gemini — y la latencia no cambia de forma medible |
| `rag_context_budget_chars` | `int` | `32000` | Presupuesto de caracteres de contexto enviado a Gemini | Limita el contexto RAG en la Fase 4. **Debe dar cabida a `rag_top_k_chunks`**: al agotarse, los fragmentos restantes se descartan en silencio (`break`), así que subir top-k sin subir esto no sirve de nada. 24 fragmentos llegan a ~26.000 chars en el peor caso medido |
| `rag_candidate_pool` | `int` | `50` | Vecinos recuperados de pgvector (`<=>`/HNSW) antes del re-rank por hardware/categoría. También fija `hnsw.ef_search`. | Pool mayor = mejor recall, algo más de cómputo |
| `system_prompt_pac` | `str` | *(ver abajo)* | Reglas de sintaxis PAC incluidas en el system prompt de Gemini | Define el comportamiento y restricciones del asistente |
| `history_max_entries` | `int` | `50` | Máximo de entradas de historial de chat por usuario | Al superarse, las entradas más antiguas se eliminan automáticamente |

> **Nota de implementación:** Todos los valores se almacenan como `TEXT` en la base de datos.
> [`services/settings/service.py`](../../apps/api/src/services/settings/service.py) los devuelve
> siempre como **string** (`get_setting_value`); el parseo a `int`/`float` lo hace el consumidor,
> `_load_chat_params` en [`services/chat/service.py`](../../apps/api/src/services/chat/service.py).
> Un valor inválido (ej. `"abc"` para `gemini_temperature`) no falla al guardarse ni al leerse de
> la BD, sino al convertirse en esa función: el endpoint `PUT` no valida el tipo, solo que el
> string no esté vacío.

> **Modelos Gemini y dimensión (no son settings de DB en caliente):** se centralizaron en
> `config.py` de API y worker como `gemini_gen_model` (`gemini-3.5-flash`),
> `gemini_embed_model` (`gemini-embedding-2`) y `gemini_embed_dim` (`3072`), overridables por
> las variables de entorno `GEMINI_GEN_MODEL` / `GEMINI_EMBED_MODEL` / `GEMINI_EMBED_DIM`
> (requiere reinicio). `gemini_embed_dim` debe coincidir con la columna `vector(N)`. El default
> sembrado de `system_prompt_pac` ya está **alineado** con la trazabilidad por IDs de fuente; las
> instalaciones existentes deben ejecutar `POST /admin/settings/reset` para adoptarlo.

---

## Cuánto aporta subir top-k

Medido sobre las tres consultas reales que fallaron en WinCaps III, contando los fragmentos que traen
**código PAC ejecutable** en vez de portadas, prefacios y folletos comerciales:

| Consulta | top6 | top12 | top18 | **top24** | top30 |
|---|---|---|---|---|---|
| VP-6242 (RC7M) | 1 | 2 | 3 | **4** | 6 |
| joint 1 a 45° | 6 | 12 | 15 | **17** | 21 |
| multitarea con entrada digital | 6 | 10 | 12 | **14** | 18 |
| chars (peor caso) | 7.588 | 14.871 | 19.823 | **25.885** | 32.371 |

> **Hay que medir por el camino real** (HyDE → embedding de `prompt + hipótesis` → retrieve). Embebiendo
> la consulta cruda salen otros números: VP-6242 se queda en 1 fragmento útil en *todos* los niveles,
> porque sin HyDE esa consulta recupera fichas de producto en vez de código. Una medición sin HyDE no
> describe lo que hace el sistema en producción.

VP-6242 rinde mucho peor que las otras dos en todos los niveles. No es un problema de top-k: es que el
corpus tiene poco código asociado a ese modelo concreto. Subir top-k lo mitiga, no lo resuelve.

Los recuentos varían un poco entre ejecuciones aunque `hyde_temperature` sea `0.0` — Gemini no es
estrictamente determinista — así que conviene leerlos como tendencia, no como cifras exactas.

---

## Valor por defecto de `system_prompt_pac`

El system prompt por defecto (`_DEFAULT_PAC_RULES`,
[settings/service.py](../../apps/api/src/services/settings/service.py)) contiene las
reglas sintácticas del PAC real tal como aparece en los programas de WinCaps III
(capítulo 9 del manual RC7):

- Directivas de preprocesador (`#INCLUDE "dio_tab.h"`, `#INCLUDE "var_tab.h"`, `#DEFINE`)
- Estructura del programa: `PROGRAM`, cuerpo terminado en `END`, y subrutinas
  definidas **después** del `END` con `*Nombre:` … `RETURN`
- Control del brazo: `TAKEARM` / `GIVEARM` (nunca `FREEARM`) y `MOTOR ON/OFF`
- Movimiento a un punto: el método de interpolación es la letra tras `MOVE` y solo
  puede ser `P` (PTP), `L` (lineal), `C` (circular) o `S` (curva libre) — `MOVE J`
  no existe. `@P`/`@0`/`@E` eligen cómo se transita el punto (pass / end /
  encoder-check), **no** significan "relativo": el relativo es aritmética sobre la
  posición actual (`P0+(0,0,-70)`)
- Movimiento por ángulo de eje: `DRIVEA (1, 45)` para absoluto ("mueve el eje 1 **a**
  45°") y `DRIVE (1, 45)` para relativo ("gira 45° **más**"). Elegir mal compila
  igual y mueve el robot a otro sitio. Pose articular completa: `J1 = (45, -30, …)`
  + `MOVE P, J1`; el constructor `J(...)` no existe
- `JUMP` para trayectorias articulares largas
- Variables **por macros de `var_tab.h`** (`I[]`, `F[]`, `C[]`); el prompt indica
  explícitamente **no** declarar locales con `DIM` salvo casos especiales
- E/S digitales: `SET IO[...]` / `RESET IO[...]` (nunca `IO[...] = ON/OFF`, que solo
  vale como condición en `IF`/`WAIT`), y los helpers `CALL dioWaitAndSet` /
  `CALL dioSetAndWait`
- Llamadas: `CALL pro2` para programa externo, `GOSUB *Rutina` para subrutina interna
- **Un `PROGRAM` por archivo**: dos en el mismo `.pac` fallan con "Plural program
  names are defined", y el `RUN` que invoque al segundo con "Wrong name". Si la tarea
  necesita varios (p. ej. multitarea con `RUN`), el prompt exige emitir un bloque
  `' ARCHIVO:` por programa y **avisarlo en el summary** — la respuesta llega como un
  único string `pac_code`, así que quien la pega entera en un archivo no compila. El
  advisory `multiple_programs_one_file` lo detecta aunque el modelo lo omita

El valor completo puede consultarse en `GET /api/v1/admin/settings/system_prompt_pac`.

---

## Comportamiento del reset

`POST /api/v1/admin/settings/reset` restaura **todos** los parámetros a sus valores por defecto
definidos en `DEFAULT_SETTINGS` del servicio. Los cambios son efectivos de inmediato para las
siguientes peticiones de chat.

---

## Auto-seed al arrancar

Al iniciar el servidor, si la tabla `system_settings` está vacía o faltan claves, el sistema
inserta automáticamente todos los parámetros con sus valores por defecto.
Esto garantiza que el pipeline funcione sin requerir configuración manual inicial.

`seed_if_empty` solo **inserta lo que falta**: nunca pisa un valor ya guardado. Por eso, cuando un
default cambia, hace falta una migración dirigida. `seed_default_settings`
([db/init.py](../../apps/api/src/db/init.py)) ejecuta cuatro después del seed:

| Función | Qué corrige |
|---|---|
| `fix_legacy_io_assignment_prompt` | El prompt guardado enseñaba `IO[...] = ON`, que no compila |
| `fix_legacy_move_prompt` | El bloque de movimiento llamaba `MOVE P` "lineal" y no cubría `DRIVE`/`DRIVEA` |
| `fix_missing_one_program_rule_prompt` | Añade la regla de un `PROGRAM` por archivo |
| `upgrade_retrieval_defaults` | Sube `rag_top_k_chunks` y `rag_context_budget_chars` |

Todas comparten el mismo criterio: **solo tocan filas que siguen en un default anterior conocido**. Un
valor puesto a propósito desde la consola admin sobrevive al despliegue. `upgrade_retrieval_defaults`
lista *todos* los defaults que han existido (`{"6", "12", "18"} → "24"`), no solo el original, porque
una instalación puede venir de cualquier versión intermedia y todas deben converger.

> **Cuidado al editar `DEFAULT_SETTINGS`:** `description` es `VARCHAR(255)`. Una descripción más larga
> hace que `seed_if_empty` lance `DataError`, e `initialize_database` lo propaga desde el `lifespan`:
> **la API no arranca**. Lo cubre `test_every_description_fits_the_column`.
