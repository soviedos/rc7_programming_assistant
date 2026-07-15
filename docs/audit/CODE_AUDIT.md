# Auditoría de Código — RC7 Programming Assistant

> Fecha: 2026-06-14 · Alcance: `apps/api`, `apps/worker`, `apps/web`, `infra`, `scripts`.
> Cada hallazgo cita archivo y línea. Severidad: **alta** / **media** / **baja**.
> "Cambia comportamiento": indica si arreglarlo altera el comportamiento en runtime.
> Las limpiezas **SEGURAS** (sin cambio de comportamiento) se aplicaron; el resto queda
> como **propuesta** pendiente de aprobación.

## Resumen

> **Actualización:** todas las propuestas accionables fueron **aplicadas** (los tests siguen
> verdes: API 76/76, worker 13/13). Solo **D2** quedó evaluado y no aplicado, con justificación.

| # | Categoría | Severidad | ¿Cambia comportamiento? | Estado |
|---|---|---|---|---|
| E1 | Docstring miente: "dimension 768" | baja | No | ✅ Aplicado |
| E2 | Test obsoleto que falla (recover stuck) | media | No (solo test) | ✅ Aplicado |
| E3 | Stream: error tras chunks parciales no se observa | baja | Sí | ✅ Aplicado (audita `CHAT_QUERY_FAILED`) |
| O1 | Setting `gemini_timeout_seconds` (DB) nunca se lee | media | Sí | ✅ Aplicado (ahora se lee y propaga) |
| O2 | Modelo `Manual` del worker sin columna `sha256` | baja | No | ✅ Aplicado |
| D1 | Strings de modelo Gemini dispersos/hardcodeados | media | Sí | ✅ Aplicado (centralizados en config) |
| D2 | `ManualStorageService` duplicado API/worker | baja | Sí | ⚖️ Evaluado · no aplicado |
| C1 | Seed `system_prompt_pac` contradice trazabilidad de `references` | media | Sí | ✅ Aplicado |
| C2 | Defaults de código ≠ defaults de `.env.example` | baja | No | Corregido |
| C3 | `delete_user` audita como `ADMIN_USER_TOGGLED` | baja | Sí | ✅ Aplicado (`ADMIN_USER_DELETED`) |
| S1 | Cap silencioso de 50 candidatos antes del re-rank | baja | Sí | ✅ Aplicado (`rag_candidate_pool`) |
| S2 | `hnsw.ef_search` no fijado (default 40) | baja | Sí | ✅ Aplicado (`SET LOCAL` por consulta) |
| S3 | Detección de duplicados descarga todos los PDF del mismo tamaño | media | Sí | ✅ Aplicado (compara `sha256` antes de descargar) |
| S4 | Revisión semántica secuencial (1 llamada Gemini por chunk) | baja | Sí | Documentado (límite de diseño) |
| S5 | Reviewer usa REST urllib; embeddings usan SDK (inconsistente) | baja | Sí | ✅ Aplicado (unificado en SDK) |

---

## 1. Errores reales

### E1 — Docstring incorrecto: "dimension 768" · `apps/worker/src/services/embeddings.py:26` · **baja** · ✅ aplicado
El docstring decía `Return one embedding vector per input text (dimension 768)`, pero
`_OUTPUT_DIMENSIONALITY = 3072` ([embeddings.py:15](../../apps/worker/src/services/embeddings.py#L15))
y la columna es `vector(3072)`. Corregido para referenciar la constante real (sin cambio de comportamiento).

### E2 — Test obsoleto que falla · `apps/worker/tests/test_ingestion.py` · **media** · ✅ aplicado
`test_recover_stuck_processing_manuals_requeues_processing` esperaba
`last_error == "Reencolado automaticamente tras reinicio del worker."`, pero el código real
`recover_stuck_processing_manuals` añade un marcador `"[crash]"`
([jobs/ingestion.py:372](../../apps/worker/src/jobs/ingestion.py#L372)); un manual recién atascado
queda exactamente como `"[crash]"`. El test fallaba contra el código actual. Se alineó la aserción
al comportamiento real (cambia el test, no el código de producción).

### E3 — Error de pipeline tras chunks parciales · `apps/api/src/api/v1/routes/chat.py:146-189` · **baja** · cambia comportamiento → propuesta
En el camino de streaming, si `stream_rag_response` lanza **después** de haber emitido algunos
eventos `chunk`, se emite un evento `error` ([chat.py:168](../../apps/api/src/api/v1/routes/chat.py#L168))
y **no** se persiste historial ni auditoría. El cliente ya recibió salida parcial. Es un comportamiento
aceptable pero no documentado; una mejora sería marcar la entrada de historial como incompleta.
No se aplica (cambia comportamiento).

---

## 2. Código huérfano / muerto

### O1 — Setting `gemini_timeout_seconds` (DB) nunca se lee · `apps/api/src/services/settings/service.py:159` · **media** · cambia comportamiento → propuesta
El catálogo de settings siembra y expone en la consola admin la clave `gemini_timeout_seconds`,
pero `get_setting_value` **nunca** se invoca para esa clave (ver usos en
[chat/service.py](../../apps/api/src/services/chat/service.py) y [chat.py](../../apps/api/src/api/v1/routes/chat.py)).
El cliente Gemini usa la variable de entorno `settings.gemini_timeout_seconds`
([core/config.py:29](../../apps/api/src/core/config.py#L29) → [chat/service.py:64](../../apps/api/src/services/chat/service.py#L64)).
**Cambiar este setting desde la consola admin no tiene ningún efecto.**
Propuesta: o bien leer el setting de DB en `_get_client`, o eliminar la clave del catálogo y documentar
que el timeout es por entorno.

### O2 — Modelo `Manual` del worker sin `sha256` · `apps/worker/src/db/models/manual.py` · **baja** · no cambia comportamiento → propuesta
La tabla `manuals` tiene columna `sha256` (definida en el modelo del API
[packages/rc7_shared_db/rc7_shared_db/models/manual.py:21](../../packages/rc7_shared_db/rc7_shared_db/models/manual.py#L21) y creada por
`init.py`). El modelo del worker **no** declara `sha256`, dando dos vistas ORM divergentes de la
misma tabla. No es un bug (el worker no usa esa columna) pero es inconsistente. Propuesta: añadir la
columna al modelo del worker por paridad, o documentar la divergencia.

> No se encontraron funciones, clases ni endpoints completamente sin referencias. Las ramas
> `regenerate` de autofix (`apply_safe_chunk_autofixes`) están intencionalmente no implementadas y
> se tratan como `keep` ([jobs/ingestion.py](../../apps/worker/src/jobs/ingestion.py)).

---

## 3. Código duplicado

### D1 — Strings de modelo Gemini dispersos · **media** · cambia comportamiento si se centraliza → propuesta
El modelo de generación `gemini-3.5-flash` y el de embeddings `gemini-embedding-2` están definidos
en varios sitios, sin una fuente única:

| Dónde | Cómo |
|---|---|
| [apps/api/src/services/chat/service.py:20-22](../../apps/api/src/services/chat/service.py#L20) | `_EMBED_MODEL`/`_GEN_MODEL` **hardcoded** |
| [apps/worker/src/services/embeddings.py:14](../../apps/worker/src/services/embeddings.py#L14) | `_EMBEDDING_MODEL` **hardcoded** |
| [apps/worker/src/services/semantic_review.py:218](../../apps/worker/src/services/semantic_review.py#L218) | `settings.gemini_model` (config) |
| [apps/worker/src/core/config.py:21](../../apps/worker/src/core/config.py#L21) | `gemini_model` (worker) |

El API **no** tiene un setting `gemini_model`. Propuesta: centralizar los nombres de modelo en
`config.py` (variables de entorno `GEMINI_MODEL`, `GEMINI_EMBEDDING_MODEL`) en ambos servicios.
No se aplica porque pasar de constante a env cambia comportamiento.

### D2 — `ManualStorageService` duplicado · `apps/api/src/services/manuals/storage.py` y `apps/worker/src/services/storage.py` · **baja** · ⚖️ evaluado · NO aplicado
Ambos servicios implementan un `ManualStorageService` casi idéntico. **Decisión: no extraer un
paquete compartido.** Ambos Dockerfiles construyen con contexto raíz pero `COPY` solo su propio
directorio (`apps/api` / `apps/worker`); un paquete común exigiría cambios coordinados en ambos
Dockerfiles, en los dos `pyproject.toml` y en el `PYTHONPATH`, acoplando dos servicios deliberadamente
separados a cambio de ~40 líneas. El riesgo de romper el build de producción supera el beneficio.
Se mantiene la duplicación intencional.

> **Deduplicación ya realizada (positivo):** la construcción de `references` que antes se repetía en
> el camino síncrono y de streaming del chat se centralizó en `_resolve_references`
> ([chat/service.py](../../apps/api/src/services/chat/service.py)).

---

## 4. Inconsistencias entre configuración y realidad

### C1 — Seed `system_prompt_pac` contradice la trazabilidad de `references` · **media** · cambia comportamiento → propuesta
El texto sembrado por defecto en `system_prompt_pac` instruye al modelo:
> "el campo 'references' debe quedar siempre como array vacío []"
([settings/service.py:134-135](../../apps/api/src/services/settings/service.py#L134)).

Pero `_build_system_prompt` **anexa** ese texto y luego añade la instrucción opuesta:
> "references → array con los IDs de fuente realmente usados (p. ej. ["S1","S3"])"
([chat/service.py:275-288](../../apps/api/src/services/chat/service.py#L275)).

El system prompt contiene instrucciones contradictorias sobre `references`. Funciona porque
`_resolve_references` corrige del lado servidor, pero confunde al modelo. Propuesta: actualizar el
texto sembrado (y los settings existentes vía reset) para alinear con la trazabilidad por IDs.

### C2 — Defaults de código ≠ defaults desplegados (`.env.example`) · **baja** · corregido
El diseño es revisar el manual completo, pero los defaults del código decían lo contrario y el
comportamiento correcto dependía de que `docker-compose.yml` cargara `.env.example` como `env_file`
antes que `.env`. Quien leyera solo `config.py` —o corriera el worker con otro `.env`— obtenía
muestreo al 10%, tope de 100 revisiones y un timeout de 420 s que no alcanza para revisar todos los
chunks de un manual grande.

Corregido en dos frentes:

1. Los defaults del código se alinearon al diseño: `semantic_review_sample_rate=1.0`,
   `semantic_review_max_reviews_per_manual=0`, `worker_manual_timeout_seconds=7200`,
   `worker_manual_timeout_max_seconds=21600` ([config.py](../../apps/worker/src/core/config.py)).
2. Se unificó la carga de entorno: `docker-compose.yml` y `docker-compose.prod.yml` cargan ambos
   solo `.env`, y `.env.example` volvió a ser plantilla. La configuración operativa vive en el
   código; los `.env` solo aportan secretos y valores propios de la máquina.

También se unificó `gemini_timeout_seconds`, que era `8` en el worker y `300` en la API: ahora ambos
usan `300`. Con revisión completa cada chunk es una llamada a Gemini, y 8 s convertía cualquier
llamada lenta en `review_status="error"` en silencio.

### C3 — `delete_user` audita como `ADMIN_USER_TOGGLED` · `apps/api/src/api/v1/routes/admin.py:377` · **baja** · cambia comportamiento → propuesta
El borrado de usuario registra `event_type="ADMIN_USER_TOGGLED"` con descripción "Usuario eliminado",
mientras crear/actualizar usan `ADMIN_USER_CREATED`/`ADMIN_USER_UPDATED`. Propuesta: usar
`ADMIN_USER_DELETED`. No se aplica porque cambia el valor registrado (filtros de auditoría existentes).

---

## 5. Riesgos de correctitud y escalabilidad

### S1 — Cap silencioso de 50 candidatos · `apps/api/src/services/chat/service.py` (`_VECTOR_CANDIDATE_POOL = 50`) · **baja** · propuesta
El retrieval recupera los 50 vecinos más cercanos por distancia coseno y **luego** re-rankea por
`hardware · categoría`. Un chunk muy relevante por hardware/categoría pero ranqueado #51+ por coseno
crudo nunca entra al re-rank. Aceptable al volumen actual; propuesta: hacer el pool configurable.

### S2 — `hnsw.ef_search` no fijado · `init.py` / `chat/service.py` · **baja** · propuesta
La búsqueda depende del `hnsw.ef_search` por defecto de pgvector (40). Para recuperar top-50 con
buena recall, conviene fijar `SET hnsw.ef_search` ≥ pool. Propuesta: fijarlo por sesión/consulta.

### S3 — Detección de duplicados descarga todos los PDF del mismo tamaño · `apps/api/src/api/v1/routes/manuals.py:68-92` · **media** · propuesta
`find_duplicate_manual_by_sha256` selecciona todos los manuales con `size_bytes` igual y **descarga
cada uno desde MinIO** para hashear y comparar. Ahora que `sha256` se almacena en la tabla, debería
compararse el `sha256` guardado **antes** de descargar (descargar solo si falta el hash). Propuesta de
optimización; reduce I/O de O(n) descargas por upload.

### S4 — Revisión semántica secuencial · `apps/worker/src/services/semantic_review.py` · **baja** · documentado
Cada chunk se revisa con una llamada HTTP individual a Gemini, en serie. Con `sample_rate=1.0` y sin
tope, un manual de 1055 chunks implica 1055 llamadas secuenciales (de ahí los timeouts elevados).
Throughput limitado por diseño; documentado.

### S5 — Acceso a Gemini inconsistente · `apps/worker/src/services/semantic_review.py:281` · **baja** · propuesta
El reviewer llama a Gemini por **REST con `urllib`** (con `temperature` hardcoded 0.1,
[semantic_review.py:288](../../apps/worker/src/services/semantic_review.py#L288)), mientras que los
embeddings usan el **SDK `google-genai`**. Dos formas de hablar con Gemini en el mismo servicio.
Propuesta: unificar en el SDK.

---

## Cambios aplicados

### Fase inicial — limpiezas seguras (sin cambio de comportamiento)
1. **E1** — Docstring `embed_texts` "768" → referencia a `_OUTPUT_DIMENSIONALITY` (3072).
2. **E2** — Aserción del test `test_recover_stuck_processing_manuals_requeues_processing` alineada al
   marcador `"[crash]"` real.

### Segunda fase — propuestas aprobadas ("todas"), con cambio de comportamiento
| # | Cambio aplicado | Archivos |
|---|---|---|
| **D1** | Modelos Gemini centralizados en config (`gemini_model`, `gemini_embedding_model`); env `GEMINI_MODEL`/`GEMINI_EMBEDDING_MODEL`. Defaults idénticos a los valores previos. | `core/config.py` (API+worker), `chat/service.py`, `embeddings.py`, `.env*.example` |
| **O1** | `gemini_timeout_seconds` (DB) ahora se lee y se propaga al cliente Gemini en las 4 fases. | `chat/service.py` |
| **C1** | Seed `system_prompt_pac` alineado con la trazabilidad por IDs (ya no pide "references vacío"). Requiere `POST /admin/settings/reset` en instalaciones existentes. | `settings/service.py` |
| **S1** | Pool de candidatos configurable vía setting `rag_candidate_pool` (default 50). | `chat/service.py`, `settings/service.py` |
| **S2** | `SET LOCAL hnsw.ef_search = max(pool, 40)` antes de la búsqueda (solo PostgreSQL). | `chat/service.py` |
| **S3** | Detección de duplicados compara `sha256` almacenado **antes** de descargar; solo descarga filas legacy sin hash. | `routes/manuals.py` |
| **C3** | Borrado de usuario audita `ADMIN_USER_DELETED`. | `routes/admin.py` |
| **O2** | Modelo `Manual` del worker declara `sha256` (paridad con el API). | `worker/db/models/manual.py` |
| **S5** | `GeminiSemanticReviewer` usa el SDK `google-genai` (no urllib). | `semantic_review.py` |
| **E3** | Error a mitad de stream ahora audita `CHAT_QUERY_FAILED`. | `routes/chat.py` |

**Tests tras los cambios:** API **76/76**, worker **13/13**.

### No aplicado
- **D2** — duplicación de `ManualStorageService`: evaluada y mantenida intencionalmente (ver arriba).
- **C2, S4** — documentados (no son defectos; son límites de diseño/entorno).
