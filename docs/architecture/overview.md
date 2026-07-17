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
| Tecnología | Next.js 16 App Router + TypeScript + Tailwind CSS (`next@16.2.4`, React 19) |
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
| Responsabilidades | Ingestión documental: parsing pypdf → chunking estructural (párrafos, anotado con la sección del outline) → revisión Gemini (todos los chunks) → embeddings → pgvector |
| Coordinación | Polling a PostgreSQL (`status = 'pending'`) con `FOR UPDATE SKIP LOCKED` para reclamar manuales |
| Resiliencia | Timeout por manual, recuperación automática de manuales atascados en `processing` al reiniciar; límite de 3 crashes consecutivos antes de marcar como `failed` |

### Paquetes compartidos — `packages/`

**`rc7_shared_db/`** — Para evitar divergencia, la `Base` declarativa, los tipos
cross-dialect (`ArrayOfString`, `EmbeddingVector`), los **modelos ORM compartidos**
(`Manual`, `ManualChunk`, `ManualChunkReview`, `ManualReviewSummary`) y las
migraciones idempotentes (`ensure_manual_columns`) tienen una **única definición**
aquí. `apps/api` y `apps/worker` lo instalan editable (ver Dockerfiles) y lo
re-exportan vía `src/db/base.py` y `src/db/models/__init__.py`, de modo que comparten
la misma `MetaData`. Los modelos propios de cada servicio (`User`, `AuditLog`,
`ChatHistory`, `RolePermission`, `SystemSetting`) viven en la API.

**`rc7_shared_config/`** — `SharedSettings` define una sola vez la configuración que
ambos servicios necesitan (Postgres, MinIO, modelos y timeout de Gemini) y las
validaciones de secretos en producción. Los `Settings` de api y worker heredan de él
y declaran solo sus campos propios, extendiendo `production_errors()` para sus
propias validaciones.

**`rc7_shared_storage/`** — `ManualStorageService` y `ManualStorageError`: el cliente
MinIO (subir, descargar y borrar el PDF de un manual, más `ensure_bucket`) con una
única definición. `apps/api/src/services/manuals/storage.py` y
`apps/worker/src/services/storage.py` son solo re-exports que le inyectan el `settings`
de su servicio.

### PostgreSQL 17 + pgvector

Base de datos transaccional y vectorial única (imagen `pgvector/pgvector:pg17`).
Tablas principales: `users`, `manuals`, `manual_chunks` (con columna
`embedding vector(3072)` + índice HNSW `manual_chunks_embedding_hnsw` sobre cast `halfvec`,
y `section_title` con la sección del manual tomada del outline del PDF),
`manual_chunk_reviews`, `manual_review_summaries`, `chat_history`,
`role_permissions`, `system_settings`, `audit_log`.

### MinIO

Almacenamiento de objetos compatible con S3 para PDFs originales. El worker descarga
desde MinIO al procesar; la API sube y sirve archivos.

### Nginx — **solo producción**

Nginx existe únicamente en `docker-compose.prod.yml` (imagen `nginx:1.27-alpine`), como
terminador TLS y reverse proxy. **El compose de desarrollo no incluye nginx**: el browser pega
directo a `web:3000` y el proxy interno de Next.js
([route.ts](../../apps/web/src/app/api/v1/[...path]/route.ts)) reenvía `/api/v1/*` a `api:8000`.
En producción nginx aplica config especial para SSE (`proxy_buffering off`,
`proxy_read_timeout`, `X-Accel-Buffering: no`).

---

## Flujo de autenticación

```text
1. Browser → POST /api/v1/auth/login (email + password)
2. API valida credenciales contra PostgreSQL (Argon2 vía `pwdlib.recommended()`)
3. API emite cookie HttpOnly con JWT firmado (HS256, TTL configurable)
4. Browser → GET /api/v1/auth/me para verificar sesión en rutas protegidas
5. Rutas admin verifican rol activo en el payload del JWT
6. POST /api/v1/auth/switch-role renueva la cookie con el rol seleccionado
```

---

## Flujo RAG (implementado)

1. Administrador carga un manual PDF → MinIO
2. Backend registra el documento con estado `pending`
3. Worker detecta el manual por polling a PostgreSQL
4. Worker descarga el PDF, extrae texto con pypdf
5. Chunking estructural: párrafos hasta 1200 chars, sin cruzar de página. La estructura del documento (outline) se usa para **anotar** la sección de cada chunk, no para decidir los cortes
6. Gemini revisa y autocorrige cada chunk
7. Chunks vectorizados con gemini-embedding-2 (3072 dim) → pgvector `vector(3072)`
8. Usuario envía consulta + configuración del robot (modelo, controlador, versión)
9. Fase 1 (HyDE): Gemini genera respuesta hipotética sin contexto documental
10. Embedding de (consulta + respuesta hipotética) → búsqueda vectorial pgvector (`<=>`, HNSW)
11. Fase 2 (Retrieval): pool top-50 por distancia coseno, re-rankeado por
    `similitud · compatibilidad de hardware · categoría` → top-k
    (top-k configurable vía módulo settings, default: 24)
12. Fase 3 (Contexto): construcción del contexto con presupuesto de caracteres
    (configurable vía módulo settings, default: 32 000 chars).
    Debe dar cabida al top-k: lo que no cabe se descarta en silencio
13. Fase 4 (Respuesta final): Gemini con contexto RAG → JSON estructurado
    con `summary`, `pac_code` y `references` — transmitido vía SSE
14. Frontend recibe chunks en tiempo real, reconstruye la respuesta

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
    └─ Extrae texto por página directamente con pypdf
    │
    ▼
build_text_chunks() → chunking estructural por párrafos + anotación de sección
    │
    ▼
GeminiSemanticReviewer → revisión de TODOS los chunks (sin muestreo por defecto):
    coherence_score, completeness_score, boundary_quality_score
    acciones: keep | merge | split | regenerate
    │
    ▼
apply_safe_chunk_autofixes() → merge / split / regenerate
    └─ regenerate: reescribe el chunk con Gemini (corrige artefactos de extracción,
       sin inventar contenido) ANTES del embedding; fail-safe a keep si falla
    │
    ▼
embed_texts() → gemini-embedding-2 en lote (un types.Content por chunk, sin task_type)
    │
    ▼
INSERT manual_chunks con embedding vector(3072)
    │ status=indexed / failed
    ▼
Listo para retrieval en próximas consultas de chat
```

> **Cancelación:** `POST /api/v1/manuals/{id}/cancel` detiene un manual en `pending` o
> `processing`, elimina sus chunks parciales y lo marca como `failed`.
> Disponible desde el botón "Detener" en la consola admin.

---

### Módulo settings

Permite configurar en tiempo real los parámetros del modelo Gemini y los prompts del
sistema desde la consola administrativa. Los cambios se persisten en la tabla
`system_settings` y se leen en cada request del pipeline RAG, sin necesidad de
reiniciar el servicio.

Ver [docs/backend/settings-module.md](../backend/settings-module.md) para la lista completa.

---

### Módulo audit

Registra eventos significativos del sistema en la tabla `audit_log`. El servicio de
auditoría nunca lanza excepciones — un fallo de logging no puede degradar el flujo
principal. Se registran acciones administrativas, eventos del pipeline de ingestión y
metadatos de consultas de chat (sin almacenar contenido de prompts o respuestas).

Ver [docs/backend/audit-module.md](../backend/audit-module.md) para la lista de eventos.

---

## Principios de diseño

| Principio | Justificación |
|---|---|
| **Simplicidad operativa** | Un solo `docker compose up` levanta todo el sistema |
| **Seguridad centralizada** | Auth y autorización resueltos exclusivamente en el backend |
| **Observabilidad** | El módulo audit registra eventos del sistema sin impactar el flujo principal (fail-safe design) |
| **Configurabilidad** | Parámetros del modelo Gemini y prompts del sistema configurables en tiempo real vía consola administrativa |
| **Streaming first** | SSE reduce la latencia percibida en respuestas largas del LLM |
| **Despliegue reproducible** | Contenedores con healthchecks y dependencias declarativas |
