# Módulo Settings — Parámetros Configurables

El módulo `settings` permite ajustar los parámetros del pipeline RAG y de Gemini en caliente,
sin reiniciar el stack. Los valores se almacenan en la tabla `system_settings` de PostgreSQL
y se leen en cada request.

---

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/admin/settings/` | Lista todos los parámetros con sus valores actuales |
| `GET` | `/api/v1/admin/settings/{key}` | Obtiene el valor de un parámetro específico |
| `PUT` | `/api/v1/admin/settings/{key}` | Actualiza el valor de un parámetro |
| `POST` | `/api/v1/admin/settings/reset` | Restaura todos los parámetros a sus valores por defecto |

Todos los endpoints requieren rol `admin`.

**Audit:** `PUT` genera evento `SETTING_UPDATED`; `POST /reset` genera evento `SETTING_RESET`.

---

## Parámetros disponibles

| Clave | Tipo | Default | Descripción | Efecto en el pipeline |
|---|---|---|---|---|
| `gemini_temperature` | `float` | `0.7` | Temperatura de generación Gemini (0.0–1.0) | Controla la aleatoriedad de las respuestas: 0.0 = determinista, 1.0 = más creativo |
| `gemini_max_tokens` | `int` | `8192` | Límite de tokens de salida en Gemini (Phase 4 fuerza `response_mime_type=application/json` para emitir JSON puro) | Respuestas truncadas si el modelo alcanza el límite; con Gemini 3.5 Flash se recomienda ≥ 8192 para código PAC completo |
| `gemini_timeout_seconds` | `int` | `300` | Timeout (segundos) de cada llamada a Gemini. **Ahora se lee** y se propaga al cliente en las 4 fases (fallback al env `GEMINI_TIMEOUT_SECONDS`). | Requests más largos fallan con timeout |
| `rag_top_k_chunks` | `int` | `12` | Chunks finales (tras re-rank) enviados como contexto | Medido sobre consultas reales: con 6 llegaban 2-4 fragmentos útiles y el resto eran portadas y prefacios; con 12 llegan 5-7. Con 18 no llegó ninguno más y desborda el presupuesto |
| `rag_context_budget_chars` | `int` | `16000` | Presupuesto de caracteres de contexto enviado a Gemini | Limita el contexto RAG en la Fase 4. **Debe dar cabida a `rag_top_k_chunks`**: al agotarse, los fragmentos restantes se descartan en silencio (`break`), así que subir top-k sin subir esto no sirve de nada |
| `rag_candidate_pool` | `int` | `50` | Vecinos recuperados de pgvector (`<=>`/HNSW) antes del re-rank por hardware/categoría. También fija `hnsw.ef_search`. | Pool mayor = mejor recall, algo más de cómputo |
| `system_prompt_pac` | `str` | *(ver abajo)* | Reglas de sintaxis PAC incluidas en el system prompt de Gemini | Define el comportamiento y restricciones del asistente |
| `history_max_entries` | `int` | `50` | Máximo de entradas de historial de chat por usuario | Al superarse, las entradas más antiguas se eliminan automáticamente |

> **Nota de implementación:** Todos los valores se almacenan como `TEXT` en la base de datos.
> El servicio `settings_service.py` se encarga de parsear a `int` o `float` según la clave
> al leer el valor. Un valor inválido (ej. `"abc"` para `gemini_temperature`) hará que la
> lectura falle; el endpoint `PUT` no valida el tipo, solo el formato de string no vacío.

> **Modelos Gemini y dimensión (no son settings de DB en caliente):** se centralizaron en
> `config.py` de API y worker como `gemini_gen_model` (`gemini-3.5-flash`),
> `gemini_embed_model` (`gemini-embedding-2`) y `gemini_embed_dim` (`3072`), overridables por
> las variables de entorno `GEMINI_GEN_MODEL` / `GEMINI_EMBED_MODEL` / `GEMINI_EMBED_DIM`
> (requiere reinicio). `gemini_embed_dim` debe coincidir con la columna `vector(N)`. El default
> sembrado de `system_prompt_pac` ya está **alineado** con la trazabilidad por IDs de fuente; las
> instalaciones existentes deben ejecutar `POST /admin/settings/reset` para adoptarlo.

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
