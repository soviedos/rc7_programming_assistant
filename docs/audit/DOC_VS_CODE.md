# Documentación vs. Código — Tabla de Divergencias

> Cada fila confronta lo que la documentación previa (README, `docs/`, comentarios) afirmaba
> contra lo que el código realmente hace, con la fuente verificable. Estado: **Corregido** (ya
> ajustado en docs), **Pendiente** (requiere decisión / cambio de comportamiento), o
> **Aclarado** (documentado tal cual está).

## Modelos de IA y embeddings

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| Generación con `gemini-2.5-flash` | `gemini-3.5-flash` | [chat/service.py:22](../../apps/api/src/services/chat/service.py#L22), [worker config.py:21](../../apps/worker/src/core/config.py#L21) | Corregido |
| Embeddings con `gemini-embedding-001` (768 dims) | `gemini-embedding-2`, 3072 dims | [chat/service.py:20-21](../../apps/api/src/services/chat/service.py#L20), [embeddings.py:14-15](../../apps/worker/src/services/embeddings.py#L14) | Corregido |
| Embedding query usa `task_type=RETRIEVAL_QUERY` | `gemini-embedding-2` no admite `task_type`; usa prefijo `"task: search result \| query:"` y `output_dimensionality=3072` | [chat/service.py:60-66](../../apps/api/src/services/chat/service.py#L60) | Corregido |
| Embedding doc usa `task_type=RETRIEVAL_DOCUMENT` | Sin `task_type`; un `types.Content` por chunk con prefijo `"title: none \| text:"` | [embeddings.py:38-49](../../apps/worker/src/services/embeddings.py#L38) | Corregido |

## Almacenamiento y recuperación vectorial

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| Columna `embedding REAL[]` | `embedding vector(3072)` (pgvector) | [api manual_chunk.py](../../packages/rc7_shared_db/rc7_shared_db/models/manual_chunk.py), [worker types.py](../../packages/rc7_shared_db/rc7_shared_db/types.py) | Corregido |
| Similitud coseno calculada en Python sobre `LIMIT 5000` | Distancia coseno `<=>` en Postgres con índice HNSW; pool top-50 re-rankeado en Python | [chat/service.py `_retrieve_chunks`](../../apps/api/src/services/chat/service.py) | Corregido |
| Boost solo por categoría documental | `score = similitud · hardware_factor · category_factor` (filtro por config del robot) | [chat/service.py `_hardware_compatibility_boost`](../../apps/api/src/services/chat/service.py) | Corregido |
| Índice HNSW pendiente / opcional | Índice HNSW creado sobre cast `halfvec(3072)` (límite de 2000 dims en `vector`) | [db/init.py `ensure_chunk_embedding_column`](../../apps/api/src/db/init.py) | Corregido |
| `references` siempre vacío `[]` | `references` lleva los IDs de fuente `S1…Sn` citados; trazabilidad inline `' fuente: SX` | [chat/service.py:275-288](../../apps/api/src/services/chat/service.py#L275) | Corregido |

## Pipeline de ingestión

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| Revisión semántica "por muestra (configurable)" | Por defecto desplegado revisa **todos** los chunks (`SEMANTIC_REVIEW_SAMPLE_RATE=1.0`, sin tope) | [.env.example], [semantic_review.py](../../apps/worker/src/services/semantic_review.py), [config.py](../../apps/worker/src/core/config.py) | Corregido |
| Worker usa `pytesseract` + `pdf2image` (OCR de PDFs escaneados) | Solo `pypdf`, extracción de texto por página; sin OCR | [parsers/pdf.py](../../apps/worker/src/parsers/pdf.py), [worker pyproject.toml](../../apps/worker/pyproject.toml) | Corregido |
| Default de `WORKER_MANUAL_TIMEOUT_SECONDS=420` | Los defaults del código contradecían el diseño (revisión completa) y el comportamiento correcto dependía de que `docker-compose.yml` cargara `.env.example` como `env_file`. Alineados al diseño: `sample_rate=1.0`, `max_reviews_per_manual=0`, `manual_timeout_seconds=7200`, `manual_timeout_max_seconds=21600`. Además se unificó la carga de entorno: ambos compose cargan solo `.env` y `.env.example` volvió a ser plantilla | [config.py](../../apps/worker/src/core/config.py), [docker-compose.yml] | Corregido (código) |
| **Antes:** autofix `regenerate` no implementado (tratado como `keep`) · **Después:** `regenerate` reescribe el chunk con Gemini (corrige artefactos de extracción, sin inventar; aplicado antes del embedding; fail-safe a `keep`; gated por `SEMANTIC_REVIEW_REGENERATE_MAX_COHERENCE`) | [jobs/ingestion.py `apply_safe_chunk_autofixes`](../../apps/worker/src/jobs/ingestion.py), [semantic_review.py `regenerate_chunk`](../../apps/worker/src/services/semantic_review.py) | Corregido (código) |
| **Antes:** reviewer llamaba a Gemini por REST urllib · **Después:** usa el SDK `google-genai` (como el embedding) | [semantic_review.py `_call_gemini`](../../apps/worker/src/services/semantic_review.py) | Corregido (código) |

## Stack y servicios

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| Frontend **Next.js 14** / luego **15** | `next@16.2.4`, `react@19.2.5` | [apps/web/package.json](../../apps/web/package.json) | Corregido |
| PostgreSQL **15** | Imagen `pgvector/pgvector:pg17` | [docker-compose.yml](../../docker-compose.yml) | Corregido |
| **Nginx** como reverse proxy del sistema (siempre) | Nginx **solo en producción** (`docker-compose.prod.yml`); el compose de desarrollo no tiene nginx — el browser pega a `web:3000` y el proxy de Next.js reenvía `/api/v1/*` a `api:8000` | [docker-compose.yml](../../docker-compose.yml) (sin nginx), [docker-compose.prod.yml:12](../../docker-compose.prod.yml#L12), [web route.ts](../../apps/web/src/app/api/v1/[...path]/route.ts) | Corregido |
| Pruebas del backend usan **SQLite en memoria** | API testea contra PostgreSQL `rc7_test` (extensión `vector`); solo el worker usa SQLite | [api tests/conftest.py](../../apps/api/tests/conftest.py), [worker tests/conftest.py](../../apps/worker/tests/conftest.py) | Corregido |

## Configuración (settings)

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| `gemini_timeout_seconds` configurable en caliente | **Corregido (código):** ahora el setting de DB se lee y se propaga al cliente Gemini en las 4 fases. Fallback al env `GEMINI_TIMEOUT_SECONDS`. | [chat/service.py `generate_rag_response`/`stream_rag_response`](../../apps/api/src/services/chat/service.py) | Corregido (CODE_AUDIT O1) |
| Nombres de modelo dispersos / API sin setting de modelo | **Centralizados** en `config.py` (API y worker) como `gemini_gen_model` (`gemini-3.5-flash`), `gemini_embed_model` (`gemini-embedding-2`) y `gemini_embed_dim` (`3072`), overridables por `GEMINI_GEN_MODEL`/`GEMINI_EMBED_MODEL`/`GEMINI_EMBED_DIM`. No quedan strings de modelo fuera de config. | [api config.py](../../apps/api/src/core/config.py), [worker config.py](../../apps/worker/src/core/config.py) | Corregido (código) |
| Settings RAG en caliente | `gemini_temperature`, `gemini_max_tokens`, `gemini_timeout_seconds`, `rag_top_k_chunks`, `rag_context_budget_chars`, `rag_candidate_pool`, `system_prompt_pac`, `history_max_entries` — todas leídas en runtime vía `get_setting_value` | [chat/service.py](../../apps/api/src/services/chat/service.py), [settings/service.py](../../apps/api/src/services/settings/service.py) | Verificado |
| **Antes:** modelos ORM duplicados en `apps/api` y `apps/worker` (riesgo de divergencia) · **Después:** una sola definición en `packages/rc7_shared_db/`; ambos servicios la re-exportan y comparten la misma `Base`/`MetaData` | [packages/rc7_shared_db](../../packages/rc7_shared_db), [api db/base.py](../../apps/api/src/db/base.py), [worker db/base.py](../../apps/worker/src/db/base.py) | Corregido (código) |
| **Antes:** índice HNSW `manual_chunks_embedding_hnsw_idx` · **Después:** renombrado a `manual_chunks_embedding_hnsw`; retrieval filtra `status='indexed'` y fija `hnsw.ef_search` | [db/init.py `ensure_chunk_embedding_column`](../../apps/api/src/db/init.py), [chat/service.py `_retrieve_chunks`](../../apps/api/src/services/chat/service.py) | Corregido (código) |

## Auth, auditoría y observabilidad

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| Google SSO | No implementado; `/auth/providers` devuelve nota "se implementará en una siguiente iteración" | [routes/auth.py:24-29](../../apps/api/src/api/v1/routes/auth.py#L24) | Verificado (pendiente) |
| Hashing de contraseñas con bcrypt | `pwdlib.PasswordHash.recommended()` (Argon2) | [auth/passwords.py:5](../../apps/api/src/services/auth/passwords.py#L5) | Corregido |
| Audit log "nunca lanza excepción" | Correcto: `log_event` captura todo y lo manda al logger | [audit_service.py:26-42](../../apps/api/src/services/audit_service.py#L26) | Verificado |
| Borrado de usuario auditado como evento de borrado | **Corregido (código):** ahora registra `ADMIN_USER_DELETED`. | [routes/admin.py](../../apps/api/src/api/v1/routes/admin.py) | Corregido (CODE_AUDIT C3) |

## Reconciliación doc↔código (auditoría sistemática)

> Revisión de los 18 documentos contra el código real: 70 discrepancias detectadas,
> 59 confirmadas tras verificación adversarial. Las de mayor impacto:

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| `CORS_ORIGINS=https://tudominio.com` como string plano en la guía de producción | `cors_origins` es `list[str]`: un string plano aborta el arranque con `SettingsError`. Debe ir en JSON siempre | [deployment.md](../operations/deployment.md), [.env.prod.example] | Corregido |
| Secret `ENV_PROD` con el `.env` de producción, y un ejemplo que lo escribe con `echo > .env` | No existe: el workflow exige que el `.env` ya esté en el servidor y **nunca** lo escribe (es deliberado). El secret que falta documentar es `SERVER_WORKDIR` | [deploy.yml:82-96](../../.github/workflows/deploy.yml) | Corregido |
| Nginx proxea `/api/v1/*` a FastAPI, y el frontend hace fetch contra Nginx | Nginx manda **todo** a `web:3000`; el enrutado a la API lo hace el proxy catch-all de Next.js | [nginx.conf:59-81](../../infra/nginx/nginx.conf) | Corregido |
| `FastAPI → MinIO` vía "presigned URL" | No existe ninguna URL prefirmada: los bytes pasan por la API (`put_object`/`get_object`) | [manuals/storage.py](../../apps/api/src/services/manuals/storage.py) | Corregido |
| Frontend en desarrollo usa `npm run dev` (Turbopack) | El servicio `web` de dev corre el build standalone igual que producción: **no hay hot reload** | [docker-compose.yml] | Corregido |
| Tests del frontend con `docker compose exec web npm test` | El contenedor `web` no lleva devDependencies: vitest no existe ahí. Se corre con `docker compose run --rm web-test` | [testing.md](../operations/testing.md) | Corregido (código y docs) |
| `actor_id` es un `UUID` | Es `int` (`Mapped[int \| None]`), y el filtro de la API lo tipa igual | [models/audit.py:19](../../apps/api/src/db/models/audit.py#L19) | Corregido |
| Cada evento de auditoría lleva su `event_metadata`, y todos incluyen `ip_address` | Solo `chat.py` pasa `metadata`; en el resto queda `NULL`. `ip_address` solo lo registran `auth.py` y `chat.py` | [routes/](../../apps/api/src/api/v1/routes/) | Corregido |
| El system prompt PAC cubre `DIM`, `MOVES`, `MOVEC`, `BITTEST`, `POSITION`, `BOOLEAN` | Ninguno de esos términos aparece en `_DEFAULT_PAC_RULES`, que además indica **no** usar `DIM` y preferir macros de `var_tab.h` | [settings/service.py:12](../../apps/api/src/services/settings/service.py#L12) | Corregido |
| `_resolve_references` descarta IDs alucinados del array `references` del modelo | Recibe solo el `source_map` y **ignora a propósito** el array del modelo; emite una entrada por cada SID | [chat/service.py:100-114](../../apps/api/src/services/chat/service.py#L100) | Corregido |
| El manual fallido guarda el detalle en `error_message` | La columna es `last_error` | [models/manual.py] | Corregido |
| La mitigación del ADR cita una capa de "repositorios" | No existe: los servicios usan la sesión de SQLAlchemy directamente | [ADR-0001](../decisions/ADR-0001-monolithic-modular-architecture.md) | Corregido |
| `packages/` contiene un solo paquete (`rc7_shared_db`) | Son **tres**: se añadieron `rc7_shared_config` (`SharedSettings` y validación de secretos) y `rc7_shared_storage` (`ManualStorageService`, el cliente MinIO) | [packages/](../../packages/) | Corregido |

## Chunking

| Afirmación previa | Realidad en el código | Fuente | Estado |
|---|---|---|---|
| La etapa 2 es "chunking semántico" | Es **estructural**: parte por página, empaqueta párrafos (`\n\n`) hasta 1200 chars y, si un párrafo excede ese tope, lo corta a ciegas cada 1200 (puede partir palabras). No entiende el texto. Lo semántico es la etapa 3, que **repara** los cortes ya hechos | [chunking/text.py](../../apps/worker/src/chunking/text.py) | Corregido |
| "Tamaño target y solapamiento configurables en código" | **No hay solapamiento**: los chunks son disjuntos. Y el tamaño (1200) es un default de parámetro que el worker nunca pasa: no existe ajuste ni en env ni en settings | [chunking/text.py:12](../../apps/worker/src/chunking/text.py#L12), [jobs/ingestion.py](../../apps/worker/src/jobs/ingestion.py) | Corregido |
| "Cada chunk lleva: texto, página de inicio, página de fin" | `TextChunk` solo tiene `page_number` (una página) y `text`. Un chunk nunca cruza de página | [chunking/text.py:6](../../apps/worker/src/chunking/text.py#L6) | Corregido |
| El embedding usa el prefijo `"title: none \| text: …"` | Ahora usa la sección del chunk: `"title: 9.7 Local Variable \| text: …"`. `manual_chunks` gana `section_title`, leído del outline del PDF. **No cambia dónde se corta**: solo anota | [embeddings.py](../../apps/worker/src/services/embeddings.py), [parsers/pdf.py](../../apps/worker/src/parsers/pdf.py) | Corregido (código) |
| `SEMANTIC_REVIEW_MAX_CHARS=2200` filtra chunks demasiado largos | **Inerte**: ningún chunk supera los 1200 chars que impone build_text_chunks, así que la razón de selección `too_long` es inalcanzable. Verificado empíricamente | [semantic_review.py](../../apps/worker/src/services/semantic_review.py), [.env.example] | Documentado |
