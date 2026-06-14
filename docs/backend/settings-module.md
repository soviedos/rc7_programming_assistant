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
| `rag_top_k_chunks` | `int` | `6` | Chunks finales (tras re-rank) enviados como contexto | Más chunks = más contexto, más costo de tokens |
| `rag_context_budget_chars` | `int` | `12000` | Presupuesto de caracteres de contexto enviado a Gemini | Limita el tamaño del contexto RAG en la Fase 4 |
| `rag_candidate_pool` | `int` | `50` | Vecinos recuperados de pgvector (`<=>`/HNSW) antes del re-rank por hardware/categoría. También fija `hnsw.ef_search`. | Pool mayor = mejor recall, algo más de cómputo |
| `system_prompt_pac` | `str` | *(ver abajo)* | Reglas de sintaxis PAC incluidas en el system prompt de Gemini | Define el comportamiento y restricciones del asistente |
| `history_max_entries` | `int` | `50` | Máximo de entradas de historial de chat por usuario | Al superarse, las entradas más antiguas se eliminan automáticamente |

> **Nota de implementación:** Todos los valores se almacenan como `TEXT` en la base de datos.
> El servicio `settings_service.py` se encarga de parsear a `int` o `float` según la clave
> al leer el valor. Un valor inválido (ej. `"abc"` para `gemini_temperature`) hará que la
> lectura falle; el endpoint `PUT` no valida el tipo, solo el formato de string no vacío.

> **Modelos Gemini (no son settings de DB en caliente):** se centralizaron en `config.py`
> (`gemini_model`, `gemini_embedding_model`), overridables por las variables de entorno
> `GEMINI_MODEL` / `GEMINI_EMBEDDING_MODEL` (requiere reinicio). El default sembrado de
> `system_prompt_pac` ya está **alineado** con la trazabilidad por IDs de fuente; las
> instalaciones existentes deben ejecutar `POST /admin/settings/reset` para adoptarlo.

---

## Valor por defecto de `system_prompt_pac`

El system prompt por defecto contiene las reglas sintácticas del lenguaje PAC para robots DENSO
RC7, incluyendo:

- Declaración de variables (`DIM`, `INTEGER`, `REAL`, `STRING`, `BOOLEAN`, `POSITION`)
- Instrucciones de movimiento (`MOVE`, `MOVES`, `MOVEC`, velocidad, `WEIGHT`, `TOOL`, `WORK`)
- Control de flujo (`IF/THEN/ELSE/END IF`, `FOR/NEXT`, `WHILE/WEND`, `GOSUB/RETURN`)
- E/S digitales (`BITTEST`, `BITSET`, `BITRESET`, `IO`)
- Funciones de posición (`HERE`, `SHIFT`, `INV`)
- Formato de respuesta JSON requerido (`summary`, `pac_code`, `references`)

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
