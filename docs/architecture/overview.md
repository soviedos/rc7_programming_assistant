# Arquitectura General

## Resumen

El proyecto implementa una arquitectura de **monolito modular con frontend separado**, ejecutado
completamente en contenedores Docker. El diseño prioriza la simplicidad operativa sobre la
flexibilidad de microservicios, adecuado para el volumen actual de manuales DENSO y usuarios.

---

## Componentes

### Frontend — `apps/web/`

| Aspecto | Detalle |
|---|---|
| Tecnología | Next.js 14 App Router + TypeScript + Tailwind CSS |
| Puerto | 3000 |
| Responsabilidades | Login, rutas protegidas, workspace del asistente PAC, consola administrativa, cambio de rol, consumidor SSE |
| Proxy API | Todas las llamadas a `/api/v1/*` pasan por el proxy interno de Next.js → `INTERNAL_API_URL=http://api:8000` |

### Backend — `apps/api/`

| Aspecto | Detalle |
|---|---|
| Tecnología | FastAPI + SQLAlchemy (sync) + Pydantic v2 |
| Puerto | 8000 |
| Responsabilidades | Autenticación, sesión JWT HttpOnly, RAG pipeline, SSE streaming, CRUD de manuales/usuarios, settings, audit |
| Módulos | `auth`, `profile`, `chat`, `manuals`, `admin`, `settings`, `audit`, `health` |

### Worker — `apps/worker/`

| Aspecto | Detalle |
|---|---|
| Tecnología | Python 3.12 + google-genai SDK + pypdf + SQLAlchemy |
| Responsabilidades | Ingestión documental: parsing pypdf → chunking semántico → revisión Gemini → embeddings → pgvector |
| Coordinación | Polling a PostgreSQL (`status = 'pending'`) con `FOR UPDATE SKIP LOCKED` para reclamar manuales |
| Resiliencia | Timeout por manual, recuperación automática de manuales atascados en `processing` al reiniciar |

### PostgreSQL 15 + pgvector

Base de datos transaccional y vectorial única. Tablas principales:
`users`, `manuals`, `manual_chunks` (con columna `embedding REAL[]`),
`manual_chunk_reviews`, `manual_review_summaries`, `chat_history`,
`role_permissions`, `system_settings`, `audit_log`.

### MinIO

Almacenamiento de objetos compatible con S3 para PDFs originales. El worker descarga
desde MinIO al procesar; la API sube y sirve archivos.

### Redis

Incluido en el stack Docker; actualmente sin consumidores activos. Reservado para
colas de tareas o caché en iteraciones futuras.

### Nginx

Reverse proxy. Configuración especial para rutas SSE (`/api/v1/chat/`):
`proxy_buffering off`, `proxy_read_timeout 310s`, `X-Accel-Buffering: no`.

---

## Flujo de autenticación

```text
1. Browser → POST /api/v1/auth/login (email + password)
2. API valida credenciales contra PostgreSQL (bcrypt via pwdlib)
3. API emite cookie HttpOnly con JWT firmado (HS256, TTL configurable)
4. Browser → GET /api/v1/auth/me para verificar sesión en rutas protegidas
5. Rutas admin verifican rol activo en el payload del JWT
6. POST /api/v1/auth/switch-role renueva la cookie con el rol seleccionado
```

---

## Flujo RAG + SSE streaming

```text
POST /api/v1/chat/generate
         │
         ▼
[Fase 1 — HyDE]
Gemini recibe la consulta del usuario (sin contexto RAG).
Genera una respuesta hipotética en texto natural.
         │
         ▼
[Fase 2 — Retrieval]
Embedding de (consulta + primeros 600 chars de la respuesta hipotética)
    → gemini-embedding-001 (768 dims, task_type=RETRIEVAL_QUERY)
    → pgvector similarity scan (coseno) sobre manual_chunks
    → top-k chunks seleccionados (k configurable, default 6)
    → boost de similitud por categoría del manual (programming ×1.30, etc.)
         │
         ▼
[Fase 3 — Context budget]
Chunks ordenados por score descendente.
Se incluyen hasta agotar el presupuesto de caracteres (default 12 000).
Formato: "[Título — pág. N]\nTexto del chunk"
         │
         ▼
[Fase 4 — Generación y streaming]
Gemini recibe system prompt (reglas PAC desde settings) + contexto RAG + consulta.
generate_content_stream() → chunks de texto yieldeados como SSE:
  data: {"type":"chunk","content":"..."}
  ...
  data: {"type":"done","summary":"...","pac_code":"...","references":[...]}

Si no hay embeddings disponibles: se usa solo el system prompt (sin RAG).
         │
         ▼
[Post-stream]
Historial guardado en chat_history (poda automática al máximo configurado).
Evento CHAT_QUERY registrado en audit_log.
```

**Fallback sin streaming** (`ENABLE_STREAMING=false`): el pipeline se ejecuta de forma
síncrona con `generate_rag_response()` y se emite un único evento `done`.

---

## Flujo de ingestión documental

```text
Admin sube PDF → POST /api/v1/manuals
    │ MinIO upload + DB insert (status=pending)
    │
    ▼
Worker polling (intervalo configurable)
    │ claim_next_pending_manual() con SELECT ... FOR UPDATE SKIP LOCKED
    │
    ▼
pypdf → extract_pdf_text_by_page()
    │
    ▼
build_text_chunks() → chunking semántico respetando párrafos
    │
    ▼
GeminiSemanticReviewer → revisión por muestra (configurable):
    coherence_score, completeness_score, boundary_quality_score
    acciones: keep | merge | split | regenerate
    │
    ▼
apply_safe_chunk_autofixes() → aplica correcciones automáticas seguras
    │
    ▼
embed_texts() → gemini-embedding-001 en lote (task_type=RETRIEVAL_DOCUMENT)
    │
    ▼
INSERT manual_chunks con embedding REAL[]
    │ status=indexed / failed
    ▼
Listo para retrieval en próximas consultas de chat
```

---

## Módulo settings

Los parámetros del pipeline RAG y de Gemini son configurables en caliente desde la
consola de administración sin reiniciar el stack. Se almacenan en la tabla
`system_settings` y se leen en cada request.

Parámetros clave: `gemini_temperature`, `gemini_max_tokens`, `rag_top_k_chunks`,
`rag_context_budget_chars`, `system_prompt_pac`, `history_max_entries`.

Ver [docs/backend/settings-module.md](../backend/settings-module.md) para la lista completa.

---

## Módulo audit

Todos los eventos de administración, autenticación y pipeline de chat se registran en
`audit_log`. El servicio `log_event()` nunca lanza excepción — los fallos de
persistencia se registran en el logger del proceso sin degradar la funcionalidad.

Ver [docs/backend/audit-module.md](../backend/audit-module.md) para la lista de eventos.

---

## Principios de diseño

| Principio | Justificación |
|---|---|
| **Simplicidad operativa** | Un solo `docker compose up` levanta todo el sistema |
| **Seguridad centralizada** | Auth y autorización resueltos exclusivamente en el backend |
| **Observabilidad sin acoplamiento** | Audit nunca rompe el flujo principal |
| **Configurabilidad en caliente** | Settings en DB eliminan reinicios para ajustar parámetros |
| **Streaming first** | SSE reduce la latencia percibida en respuestas largas del LLM |
| **Despliegue reproducible** | Contenedores con healthchecks y dependencias declarativas |
